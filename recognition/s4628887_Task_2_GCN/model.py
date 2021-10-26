import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dropout
from GCNConv import GCNConv


def GCN_model(F, N, num_classes):
    """
    :param F: Number of features
    :param N: Number of nodes
    :param num_classes: Number of classes
    :return: a multi-layer GCN model
    """

    # Parameters
    channels_1 = 32          # Number of channels in the first GCN layer
    channels_2 = 8           # Number of channels in the second GCN layer
    dropout = 0.5           # Dropout rate for the features

    # Model definition
    X_in = Input(shape=(F, ))
    node_in = Input((N, ), sparse=True)

    dropout_1 = Dropout(dropout)(X_in)
    GCNconv_1 = GCNConv(channels_1, activation='relu')([dropout_1, node_in])

    dropout_2 = Dropout(dropout)(GCNconv_1)
    GCNconv_2 = GCNConv(channels_2, activation='relu')([dropout_2, node_in])

    dropout_3 = Dropout(dropout)(GCNconv_2)
    GCNconv_3 = GCNConv(num_classes, activation='softmax')([dropout_3, node_in])

    # Build model
    model = Model(inputs=[X_in, node_in], outputs=GCNconv_3)
    
    return model
