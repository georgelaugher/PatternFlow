import random

import myGraphModel
import tensorflow as tf

from tensorflow.keras import losses
import tensorflow.keras.optimizers as op
import scipy.sparse as spr
import numpy as np

from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

# ========================= GLOBAL VARIABLES =========================
# !!! IMPORTANT !!!
# Ensure valid file path to facebook.npz here
FILE_PATH = r"./resources/facebook.npz"

# Plotting Variables
PLOT_TSNE = True  # Set whether or not you want to plot accuracy
PLOT_ACCURACY = True  # Set whether or not you want to plot accuracy

# model Variables
EPOCHS = 200  # Set the number of epochs over which the Model should train
LEARNING_RATE = 0.01  # Set the Model learning rate

# Data Splitting Variables
TRAIN_SPLIT = 0.80
TEST_VAL_SPLIT = 0.20
# ====================================================================


def coo_matrix_to_sparse_tensor(coo):
    indices = np.mat([coo.row, coo.col]).transpose()
    return tf.SparseTensor(indices, coo.data, coo.shape)


def normalize_adjacency_matrix(a_bar):
    row_sum = np.array(a_bar.sum(1))
    d_inv_sqr = np.power(row_sum, -0.5).flatten()
    d_inv_sqr[np.isinf(d_inv_sqr)] = 0
    d_mat_inv_sqrt = spr.diags(d_inv_sqr)
    a_bar = a_bar.dot(d_mat_inv_sqrt).transpose().dot(d_mat_inv_sqrt).tocoo()
    return a_bar


def summarise_data(data, aspect):
    print(f"===== {aspect} =====")
    aspect_d = data[aspect]
    print(aspect_d.shape)  # (22 470, 128)
    print(aspect_d)
    print(type(aspect_d))
    print(type(aspect_d[0]))
    print(aspect_d[0])
    print("====================")


def generate_tsne_plot(labels, feats, mode):
    # TSNE
    print("Executing TSNE, this might take a moment...")
    tsne = TSNE(2)
    tsne_data = tsne.fit_transform(feats)

    plt.figure(figsize=(6, 5))
    plt.scatter(tsne_data[labels == 0, 0], tsne_data[labels == 0, 1], c='b', alpha=0.5, marker='.', label='TV Show')
    plt.scatter(tsne_data[labels == 1, 0], tsne_data[labels == 1, 1], c='r', alpha=0.5, marker='.', label='Company')
    plt.scatter(tsne_data[labels == 2, 0], tsne_data[labels == 2, 1], c='g', alpha=0.5, marker='.', label='Government')
    plt.scatter(tsne_data[labels == 3, 0], tsne_data[labels == 3, 1], c='m', alpha=0.5, marker='.', label='Politician')
    plt.title(f"GCN TSNE Plot ({mode} Data)")
    plt.legend()
    plt.show()


def generate_accuracy_plot(history):
    plt.plot(history.history['accuracy'], label='Test Accuracy')
    plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
    plt.title("GCN Accuracy over epochs")
    plt.ylabel("Accuracy")
    plt.xlabel("Epochs")
    plt.legend()
    plt.show()


def shuffle(page_one, page_two, feats, labels):
    z = list(zip(page_one, page_two, feats, labels))
    random.shuffle(z)
    page_one, page_two, feats, labels = zip(*z)

    return page_one, page_two, feats, labels


def parse_data(data, train_val_split):
    # Adjacency Matrix
    # Split EdgeList into two tensors
    page_one = data['edges'][:, 0]
    page_two = data['edges'][:, 1]
    # Features
    feats = tf.convert_to_tensor(data['features'])
    # Labels
    labels = tf.convert_to_tensor(data['target'])

    # Split Data
    # Data needs to be manually split here because the current implementation requires
    page_one, page_two, feats, labels = shuffle(page_one, page_two, feats, labels)

    page_one = tf.convert_to_tensor(page_one)
    page_two = tf.convert_to_tensor(page_two)
    feats = tf.convert_to_tensor(feats)
    labels = tf.convert_to_tensor(labels)

    # Convert split percentage into integer
    print(labels.shape[0])
    split_t = int(round(labels.shape[0] * (1 - train_val_split)))

    train_labels, test_labels = labels[:split_t], labels[split_t:]
    train_feats, test_feats = feats[:split_t], feats[split_t:]

    # Convert EdgeList to Sparse Adjacency Matrix
    ones = tf.ones_like(page_one)  # Create Ones Matrix to set
    a_bar = spr.coo_matrix((ones, (page_one, page_two)))  # Convert to SciPy COO Matrix
    a_bar.setdiag(1)  # Make all nodes adjacent to themselves

    a_dense = a_bar.todense()  # Convert to Dense to  easily split into test/train

    # Re-create two adjacency matrices for training/testing
    a_bar = a_dense[:split_t, :split_t]
    a_bar_test = a_dense[split_t-1:, split_t-1:]

    # Convert back to COO Matrix
    a_bar = spr.coo_matrix(a_bar)
    a_bar_test = spr.coo_matrix(a_bar_test)

    # Normalize
    a_bar = normalize_adjacency_matrix(a_bar=a_bar)
    a_bar_test = normalize_adjacency_matrix(a_bar=a_bar_test)

    # Convert to Sparse Tensor
    a_bar = coo_matrix_to_sparse_tensor(a_bar)
    a_bar_test = coo_matrix_to_sparse_tensor(a_bar_test)

    return train_feats, train_labels, a_bar, test_feats, test_labels, a_bar_test


def ensure_valid_split(train, test):
    if train+test == 1.0:
        return True
    else:
        print("Train Split + Validation Split + Test Split must equal 1.0.")
        print("Please ensure values for these variables sum to 1.0")
        exit(1)


def main():
    print("Tensorflow version:", tf.__version__)
    print("Numpy version:", np.__version__)

    # Variables
    ensure_valid_split(TEST_VAL_SPLIT, TRAIN_SPLIT)

    # Load in Data
    data = np.load(FILE_PATH)
    # There are 22 470 Pages
    # Each with 128 features
    # Each falls into 1 of 4 categories
    # # 0 -> TV Show
    # # 1 -> Company
    # # 2 -> Government
    # # 3 -> Politician
    # There are 342 004 Edges between the pages

    # test_split = 0.2
    train_feats, train_labels, a_bar, \
        test_feats, test_labels, a_bar_test, = parse_data(data, TEST_VAL_SPLIT)

    # ================== REAL MODEL ========================
    print("=============== Building Model ===============")
    # Construct Model
    my_model = myGraphModel.makeMyModel(a_bar, a_bar_test, train_feats)

    loss_fn = losses.SparseCategoricalCrossentropy(from_logits=False)
    opt = op.Adam(learning_rate=LEARNING_RATE)
    my_model.compile(optimizer=opt, loss=loss_fn, metrics=['accuracy'])

    # ================== RUN MODEL ========================
    # Train Model
    history = my_model.fit(train_feats,
                            train_labels,
                           epochs=EPOCHS,
                           batch_size=22470, shuffle=False,
                           validation_data=(test_feats, test_labels))

    print(my_model.summary())

    # Evaluate Model
    my_model.evaluate(test_feats,
                      test_labels,
                      batch_size=22470)

    # Plot Accuracy
    if PLOT_ACCURACY:
        generate_accuracy_plot(history)

    # Plot TSNE
    if PLOT_TSNE:
        generate_tsne_plot(train_labels, train_feats, "Train")
        generate_tsne_plot(test_labels, test_feats, "Test")


if __name__ == '__main__':
    main()

