import warnings
import pickle
import numpy as np
import lasagne
from lasagne.layers import InputLayer, DenseLayer, NonlinearityLayer,\
    DropoutLayer
from lasagne.layers import set_all_param_values
try:
    from lasagne.layers.dnn import Conv2DDNNLayer as ConvLayer
except ImportError:
    warnings.warn("cuDNN not available, using theano's conv2d instead.")
    from lasagne.layers import Conv2DLayer as ConvLayer
from lasagne.layers import Pool2DLayer as PoolLayer
from lasagne.nonlinearities import softmax, LeakyRectify

from lasagne.layers.dnn import MaxPool2DDNNLayer
from lasagne.layers import FeaturePoolLayer
from lasagne.layers import ConcatLayer
from lasagne.layers import ReshapeLayer

def vgg19(input_var=None, filename=None, n_classes=1000, p=None):
    """Setup network structure for VGG19 and optionally load pretrained
    weights

    Parameters
    ----------
    input_var : Theano symbolic variable or `None` (default: `None`)
        A variable representing a network input. If it is not provided, a
        variable will be created.
    filename : Optional[str]
        if filename is not None, weights are loaded from filename
    n_classes : Optional[int]
        default 1000 for weights trained on ImageNet
    p : float [0,1] (default: 'None')
        if p is not none, we use dropout layers with probability p

    Returns
    -------
    dict
        one lasagne layer per key

    Notes
    -----
        Reference: Simonyan & Zisserman, 2015: "Very Deep Convolutional
        Networks for Large-Scale Image Recognition"
        This function is based on:
            https://gist.github.com/ksimonyan/3785162f95cd2d5fee77
        License: non-commercial use only
        Download pretrained weights from:
        https://s3.amazonaws.com/lasagne/recipes/pretrained/imagenet/vgg19.pkl

    """

    net = {}
    net['input'] = InputLayer((None, 3, 224, 224), input_var=input_var)
    net['conv1_1'] = ConvLayer(net['input'], 64, 3, pad=1)
    net['conv1_2'] = ConvLayer(net['conv1_1'], 64, 3, pad=1)
    net['pool1'] = PoolLayer(net['conv1_2'], 2)
    net['conv2_1'] = ConvLayer(net['pool1'], 128, 3, pad=1)
    net['conv2_2'] = ConvLayer(net['conv2_1'], 128, 3, pad=1)
    net['pool2'] = PoolLayer(net['conv2_2'], 2)
    net['conv3_1'] = ConvLayer(net['pool2'], 256, 3, pad=1)
    net['conv3_2'] = ConvLayer(net['conv3_1'], 256, 3, pad=1)
    net['conv3_3'] = ConvLayer(net['conv3_2'], 256, 3, pad=1)
    net['conv3_4'] = ConvLayer(net['conv3_3'], 256, 3, pad=1)
    net['pool3'] = PoolLayer(net['conv3_4'], 2)
    net['conv4_1'] = ConvLayer(net['pool3'], 512, 3, pad=1)
    net['conv4_2'] = ConvLayer(net['conv4_1'], 512, 3, pad=1)
    net['conv4_3'] = ConvLayer(net['conv4_2'], 512, 3, pad=1)
    net['conv4_4'] = ConvLayer(net['conv4_3'], 512, 3, pad=1)
    net['pool4'] = PoolLayer(net['conv4_4'], 2)
    net['conv5_1'] = ConvLayer(net['pool4'], 512, 3, pad=1)
    net['conv5_2'] = ConvLayer(net['conv5_1'], 512, 3, pad=1)
    net['conv5_3'] = ConvLayer(net['conv5_2'], 512, 3, pad=1)
    net['conv5_4'] = ConvLayer(net['conv5_3'], 512, 3, pad=1)
    net['pool5'] = PoolLayer(net['conv5_4'], 2)
    net['fc6'] = DenseLayer(net['pool5'], num_units=4096)

    if p is None:
        net['fc7'] = DenseLayer(net['fc6'], num_units=4096)
        net['fc8'] = DenseLayer(net['fc7'], num_units=n_classes,
                                nonlinearity=None)

    else:
        net['dropout1'] = DropoutLayer(net['fc6'], p=p)
        net['fc7'] = DenseLayer(net['dropout1'], num_units=4096)
        net['dropout2'] = DropoutLayer(net['fc7'], p=p)
        net['fc8'] = DenseLayer(net['dropout2'], num_units=n_classes,
                                nonlinearity=None)
    net['prob'] = NonlinearityLayer(net['fc8'], softmax)

    if filename is not None:
        load_weights(net['prob'], filename)

    return net


def vgg19_fc7_to_prob(input_var=None, filename=None,
                      n_classes=5):
    """Setup network structure for VGG19 layers fc7 and softmax output

       Input is supposed to be feature activations of fc6 layer from VGG19

    Parameters
    ----------
    input_var : Theano symbolic variable or `None` (default: `None`)
        A variable representing a network input. If it is not provided, a
        variable will be created.
    filename : Optional[str]
        if filename is not None, weights are loaded from filename
    n_classes : Optional[int]
        default 5 for transfer learning on Kaggle DR data

    Returns
    -------
    dict
        one lasagne layer per key

    """

    net = {}
    net['input'] = InputLayer((None, 4096), input_var=input_var)
    net['fc7'] = DenseLayer(net['input'], num_units=4096)
    net['fc8'] = DenseLayer(net['fc7'], num_units=n_classes, nonlinearity=None)
    net['prob'] = NonlinearityLayer(net['fc8'], softmax)

    if filename is not None:
        load_weights(net['prob'], filename)

    return net


def vgg19_fc8_to_prob(input_var=None, filename=None,
                      n_classes=5):
    """Setup network structure for retraining last layer of VGG19

       Input is supposed to be feature activations of fc7 layer from VGG19
       The network architecture is equivalent to logistic regression

    Parameters
    ----------
    batch_size : optional[int]
        if None, not known at compile time
    input_var : Theano symbolic variable or `None` (default: `None`)
        A variable representing a network input. If it is not provided, a
        variable will be created.
    filename : Optional[str]
        if filename is not None, weights are loaded from filename
    n_classes : Optional[int]
        default 5 for transfer learning on Kaggle DR data

    Returns
    -------
    dict
        one lasagne layer per key

    """

    net = {}
    net['input'] = InputLayer((None, 4096), input_var=input_var)
    net['fc8'] = DenseLayer(net['input'], num_units=n_classes,
                            nonlinearity=None)
    net['prob'] = NonlinearityLayer(net['fc8'], softmax)

    if filename is not None:
        load_weights(net['prob'], filename)

    return net


def jeffrey_df(input_var=None, width=512, height=512,
               filename=None, n_classes=5, batch_size=None):
    """Setup network structure for JeffreyDF's network and optionally load
    pretrained weights

    Parameters
    ----------
    input_var : Theano symbolic variable or `None` (default: `None`)
        A variable representing a network input. If it is not provided, a
        variable will be created.
    width : Optional[int]
        image width
    height : Optional[int]
        image height
    filename : Optional[str]
        if filename is not None, weights are loaded from filename
    n_classes : Optional[int]
        default 5 for transfer learning on Kaggle DR data

    Returns
    -------
    dict
        one lasagne layer per key

    Notes
    -----
        Reference: Jeffrey De Fauw, 2015:
        http://jeffreydf.github.io/diabetic-retinopathy-detection/

        Download pretrained weights from:
        https://github.com/JeffreyDF/kaggle_diabetic_retinopathy/blob/master/
        dumps/2015_07_17_123003_PARAMSDUMP.pkl

       original net has leaky rectifier units

    """

    net = {}

    net['0'] = InputLayer((batch_size, 3, width, height), input_var=input_var,
                          name='images')
    net['1'] = ConvLayer(net['0'], 32, 7, stride=(2, 2), pad='same',
                         untie_biases=True,
                         nonlinearity=LeakyRectify(leakiness=0.5),
                         W=lasagne.init.Orthogonal(1.0),
                         b=lasagne.init.Constant(0.1))
    net['2'] = MaxPool2DDNNLayer(net['1'], 3, stride=(2, 2))
    net['3'] = ConvLayer(net['2'], 32, 3, stride=(1, 1), pad='same',
                         untie_biases=True,
                         nonlinearity=LeakyRectify(leakiness=0.5),
                         W=lasagne.init.Orthogonal(1.0),
                         b=lasagne.init.Constant(0.1))
    net['4'] = ConvLayer(net['3'], 32, 3, stride=(1, 1), pad='same',
                         untie_biases=True,
                         nonlinearity=LeakyRectify(leakiness=0.5),
                         W=lasagne.init.Orthogonal(1.0),
                         b=lasagne.init.Constant(0.1))
    net['5'] = MaxPool2DDNNLayer(net['4'], 3, stride=(2, 2))
    net['6'] = ConvLayer(net['5'], 64, 3, stride=(1, 1), pad='same',
                         untie_biases=True,
                         nonlinearity=LeakyRectify(leakiness=0.5),
                         W=lasagne.init.Orthogonal(1.0),
                         b=lasagne.init.Constant(0.1))
    net['7'] = ConvLayer(net['6'], 64, 3, stride=(1, 1), pad='same',
                         untie_biases=True,
                         nonlinearity=LeakyRectify(leakiness=0.5),
                         W=lasagne.init.Orthogonal(1.0),
                         b=lasagne.init.Constant(0.1))
    net['8'] = MaxPool2DDNNLayer(net['7'], 3, stride=(2, 2))
    net['9'] = ConvLayer(net['8'], 128, 3, stride=(1, 1), pad='same',
                         untie_biases=True,
                         nonlinearity=LeakyRectify(leakiness=0.5),
                         W=lasagne.init.Orthogonal(1.0),
                         b=lasagne.init.Constant(0.1))
    net['10'] = ConvLayer(net['9'], 128, 3, stride=(1, 1), pad='same',
                          untie_biases=True,
                          nonlinearity=LeakyRectify(leakiness=0.5),
                          W=lasagne.init.Orthogonal(1.0),
                          b=lasagne.init.Constant(0.1))
    net['11'] = ConvLayer(net['10'], 128, 3, stride=(1, 1), pad='same',
                          untie_biases=True,
                          nonlinearity=LeakyRectify(leakiness=0.5),
                          W=lasagne.init.Orthogonal(1.0),
                          b=lasagne.init.Constant(0.1))
    net['12'] = ConvLayer(net['11'], 128, 3, stride=(1, 1), pad='same',
                          untie_biases=True,
                          nonlinearity=LeakyRectify(leakiness=0.5),
                          W=lasagne.init.Orthogonal(1.0),
                          b=lasagne.init.Constant(0.1))
    net['13'] = MaxPool2DDNNLayer(net['12'], 3, stride=(2, 2))
    net['14'] = ConvLayer(net['13'], 256, 3, stride=(1, 1), pad='same',
                          untie_biases=True,
                          nonlinearity=LeakyRectify(leakiness=0.5),
                          W=lasagne.init.Orthogonal(1.0),
                          b=lasagne.init.Constant(0.1))
    net['15'] = ConvLayer(net['14'], 256, 3, stride=(1, 1), pad='same',
                          untie_biases=True,
                          nonlinearity=LeakyRectify(leakiness=0.5),
                          W=lasagne.init.Orthogonal(1.0),
                          b=lasagne.init.Constant(0.1))
    net['16'] = ConvLayer(net['15'], 256, 3, stride=(1, 1), pad='same',
                          untie_biases=True,
                          nonlinearity=LeakyRectify(leakiness=0.5),
                          W=lasagne.init.Orthogonal(1.0),
                          b=lasagne.init.Constant(0.1))
    net['17'] = ConvLayer(net['16'], 256, 3, stride=(1, 1), pad='same',
                          untie_biases=True,
                          nonlinearity=LeakyRectify(leakiness=0.5),
                          W=lasagne.init.Orthogonal(1.0),
                          b=lasagne.init.Constant(0.1))
    net['18'] = MaxPool2DDNNLayer(net['17'], 3, stride=(2, 2),
                                  name='coarse_last_pool')
    net['19'] = DropoutLayer(net['18'], p=0.5)
    net['20'] = DenseLayer(net['19'], num_units=1024, nonlinearity=None,
                           W=lasagne.init.Orthogonal(1.0),
                           b=lasagne.init.Constant(0.1),
                           name='first_fc_0')
    net['21'] = FeaturePoolLayer(net['20'], 2)
    net['22'] = InputLayer((batch_size, 2), name='imgdim')
    net['23'] = ConcatLayer([net['21'], net['22']])
    #Combine representations of both eyes
    net['24'] = ReshapeLayer(net['23'], (-1, net['23'].output_shape[1]*2))
    net['25'] = DropoutLayer(net['24'], p=0.5)
    net['26'] = DenseLayer(net['25'], num_units=1024, nonlinearity=None,
                           W=lasagne.init.Orthogonal(1.0),
                           b=lasagne.init.Constant(0.1),
                           name='combine_repr_fc')
    net['27'] = FeaturePoolLayer(net['26'], 2)
    net['28'] = DropoutLayer(net['27'], p=0.5)
    net['29'] = DenseLayer(net['28'],

                           num_units=n_classes * 2,
                           nonlinearity=None,
                           W=lasagne.init.Orthogonal(1.0),
                           b=lasagne.init.Constant(0.1))
    # Reshape back to the number of desired classes
    net['30'] = ReshapeLayer(net['29'], (-1, n_classes))
    net['31'] = NonlinearityLayer(net['30'], nonlinearity=softmax)
    
    if filename is not None:
        with open(filename, 'r') as f:
            weights = pickle.load(f)
        set_all_param_values(net['31'], weights)

    return net


def load_weights(layer, filename):
    """
    Load network weights from either a pickle or a numpy file and set
    the parameters of all layers below layer (including the layer itself)
    to the given values.

    Parameters
    ----------
    layer : Layer
        The :class:`Layer` instance for which to set all parameter values
    filename : str with ending .pkl or .npz

    """

    if filename.endswith('.npz'):
        with np.load(filename) as f:
            param_values = [f['arr_%d' % i] for i in range(len(f.files))]
        set_all_param_values(layer, param_values)
        return

    if filename.endswith('.pkl'):
        with open(filename) as handle:
            model = pickle.load(handle)
        set_all_param_values(layer, model['param values'])
        return

    raise NotImplementedError('Format of {filename} not known'.format(
        filename=filename))