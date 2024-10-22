# models.py

import numpy as np
import collections
import torch
import torch.nn as nn
import random


#####################
# MODELS FOR PART 1 #
#####################

class ConsonantVowelClassifier(object):
    def predict(self, context):
        """
        :param context:
        :return: 1 if vowel, 0 if consonant
        """
        raise Exception("Only implemented in subclasses")


class FrequencyBasedClassifier(ConsonantVowelClassifier):
    """
    Classifier based on the last letter before the space. If it has occurred with more consonants than vowels,
    classify as consonant, otherwise as vowel.
    """
    def __init__(self, consonant_counts, vowel_counts):
        self.consonant_counts = consonant_counts
        self.vowel_counts = vowel_counts

    def predict(self, context):
        # Look two back to find the letter before the space
        if self.consonant_counts[context[-1]] > self.vowel_counts[context[-1]]:
            return 0
        else:
            return 1


class RNNClassifier(ConsonantVowelClassifier, nn.Module):
    def __init__(self, input_size, unique_charactor_amount, hidden_size, hidden_layer1,  vocab_index):
        super(RNNClassifier, self).__init__()
        self.charactor_embedding = nn.Embedding(num_embeddings=unique_charactor_amount, embedding_dim=input_size)
        self.lstm = nn.LSTM(input_size=input_size,      # embedding dimension
                            hidden_size=hidden_size,             # Number of LSTM units
                            num_layers=1,               # Number of LSTM layers
                            batch_first=True)           # Input shape will be [batch_size, seq_length, input_size]
        self.dropout = nn.Dropout(p=0.5)
        self.relu = nn.ReLU()
        self.linear = nn.Linear(hidden_size, hidden_layer1)
        self.linear2 = nn.Linear(hidden_layer1, 2)
        self.vocab_index = vocab_index

    def forward(self, x):
        embedded_vector = self.charactor_embedding(x)
        output, (hidden, cell) = self.lstm(embedded_vector)

        hidden = hidden.squeeze()

        val = self.linear(hidden)

        val = self.relu(val)

        val =  self.dropout(val)

        predicted_val =  self.linear2(val)

        return predicted_val


    def predict(self, context):
        index_string = torch.FloatTensor([self.vocab_index.index_of(x) for x in context]).int()

        predicted = self.forward(index_string)

        predicted_class = torch.argmax(predicted)

        return predicted_class
        # raise Exception("Implement me")

def train_frequency_based_classifier(cons_exs, vowel_exs):
    consonant_counts = collections.Counter()
    vowel_counts = collections.Counter()
    for ex in cons_exs:
        consonant_counts[ex[-1]] += 1
    for ex in vowel_exs:
        vowel_counts[ex[-1]] += 1
    return FrequencyBasedClassifier(consonant_counts, vowel_counts)


def raw_string_to_indices(train_cons, train_vowel, vocab_index):
   cons_data = [[train_cons[index], 0 , index] for index in range(0, len(train_cons))]
   vowels_data = [[train_vowel[index], 1 , len(train_cons) + index] for index in range(0, len(train_vowel))]

   all_data = cons_data + vowels_data

   for index in all_data:
       index_string = [vocab_index.index_of(x)for x in index[0]]
       index.append(index_string)

   return all_data


def train_rnn_classifier(args, train_cons_exs, train_vowel_exs, dev_cons_exs, dev_vowel_exs, vocab_index):
    """
    :param args: command-line args, passed through here for your convenience
    :param train_cons_exs: list of strings followed by consonants
    :param train_vowel_exs: list of strings followed by vowels
    :param dev_cons_exs: list of strings followed by consonants
    :param dev_vowel_exs: list of strings followed by vowels
    :param vocab_index: an Indexer of the character vocabulary (27 characters)
    :return: an RNNClassifier instance trained on the given data
    """

    data = raw_string_to_indices(train_cons_exs, train_vowel_exs, vocab_index)

    n_samples = len(data)
    n_test_samples = len(dev_cons_exs) + len(dev_vowel_exs)
    epochs = 20
    batch_size = 4
    unique_charactor_amount = vocab_index.__len__()

    rnn_classification_model = RNNClassifier(input_size=30, unique_charactor_amount=unique_charactor_amount, hidden_size=32,hidden_layer1=16, vocab_index=vocab_index)

    loss_function = nn.CrossEntropyLoss()

    optimizer = torch.optim.Adam(rnn_classification_model.parameters(), lr=0.005)

    random.seed(10)

    for epoch in range(epochs):
        rnn_classification_model.train()
        total_loss = 0
        random.shuffle(data)

        for i in range(0, n_samples, batch_size):
            batch_data = data[i:min(i + batch_size, n_samples)]

            batch_index_data = torch.LongTensor([x[3] for x in batch_data])
            batch_label = torch.LongTensor([x[1] for x in batch_data])

            optimizer.zero_grad()
            y = rnn_classification_model(batch_index_data)
            loss = loss_function(y, batch_label)
            total_loss += loss.item()

            loss.backward()
            optimizer.step()

        # Calculate average loss properly accounting for possibly incomplete final batch
        n_batches = (n_samples + batch_size - 1) // batch_size
        avg_loss = total_loss / n_batches

        # Evaluation phase
        rnn_classification_model.eval()
        with torch.no_grad():
            correct_train = 0
            for index in train_cons_exs:
                predicted_val = rnn_classification_model.predict(index)
                if predicted_val == 0:
                    correct_train += 1

            for index in train_vowel_exs:
                predicted_val = rnn_classification_model.predict(index)
                if predicted_val == 1:
                    correct_train += 1

            correct_test = 0
            for index in dev_cons_exs:
                predicted_val = rnn_classification_model.predict(index)
                if predicted_val == 0:
                    correct_test += 1

            for index in dev_vowel_exs:
                predicted_val = rnn_classification_model.predict(index)
                if predicted_val == 1:
                    correct_test += 1

        print(f'Epoch {epoch + 1}:')
        print(f'Training Loss: {avg_loss:.4f}')
        print(f'Training Accuracy: {correct_train / n_samples:.3f}')
        print(f'Test Accuracy: {correct_test / n_test_samples:.3f}')

    return rnn_classification_model


#####################
# MODELS FOR PART 2 #
#####################


class LanguageModel(object):

    def get_log_prob_single(self, next_char, context):
        """
        Scores one character following the given context. That is, returns
        log P(next_char | context)
        The log should be base e
        :param next_char:
        :param context: a single character to score
        :return:
        """
        raise Exception("Only implemented in subclasses")


    def get_log_prob_sequence(self, next_chars, context):
        """
        Scores a bunch of characters following context. That is, returns
        log P(nc1, nc2, nc3, ... | context) = log P(nc1 | context) + log P(nc2 | context, nc1), ...
        The log should be base e
        :param next_chars:
        :param context:
        :return:
        """
        raise Exception("Only implemented in subclasses")


class UniformLanguageModel(LanguageModel):
    def __init__(self, voc_size):
        self.voc_size = voc_size

    def get_log_prob_single(self, next_char, context):
        return np.log(1.0/self.voc_size)

    def get_log_prob_sequence(self, next_chars, context):
        return np.log(1.0/self.voc_size) * len(next_chars)


class RNNLanguageModel(LanguageModel):
    def __init__(self, model_emb, model_dec, vocab_index):
        self.model_emb = model_emb
        self.model_dec = model_dec
        self.vocab_index = vocab_index

    def get_log_prob_single(self, next_char, context):
        raise Exception("Implement me")

    def get_log_prob_sequence(self, next_chars, context):
        raise Exception("Implement me")


def train_lm(args, train_text, dev_text, vocab_index):
    """
    :param args: command-line args, passed through here for your convenience
    :param train_text: train text as a sequence of characters
    :param dev_text: dev texts as a sequence of characters
    :param vocab_index: an Indexer of the character vocabulary (27 characters)
    :return: an RNNLanguageModel instance trained on the given data
    """

    raise Exception("Implement me")
