# Copyright (c) 2017 NVIDIA Corporation
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.nn.init as weight_init
from torch.autograd import Variable

def activation(input, kind):
  if kind == 'selu':
    return F.selu(input)
  elif kind == 'relu':
    return F.relu(input)
  elif kind == 'relu6':
    return F.relu6(input)
  elif kind == 'sigmoid':
    return F.sigmoid(input)
  elif kind == 'tanh':
    return F.tanh(input)
  elif kind == 'elu':
    return F.elu(input)
  elif kind == 'lrelu':
    return F.leaky_relu(input)
  elif kind == 'none':
    return input
  else:
    raise ValueError('Unknown non-linearity type')

def MSEloss(inputs, targets, size_avarage=False):
  mask = targets != 0
  num_ratings = torch.sum(mask.float())
  criterion = nn.MSELoss(size_average=size_avarage)
  return criterion(inputs * mask.float(), targets), Variable(torch.Tensor([1.0])) if size_avarage else num_ratings

class AutoEncoder(nn.Module):
  def __init__(self, layer_sizes, nl_type='selu', is_constrained=True, dp_drop_prob=0.0):
    super(AutoEncoder, self).__init__()
    self._dp_drop_prob = dp_drop_prob
    if dp_drop_prob > 0:
      self.drop = nn.Dropout(dp_drop_prob)
    self._last = len(layer_sizes) - 2
    self._nl_type = nl_type
    self.encode_w = nn.ParameterList(
      [nn.Parameter(torch.rand(layer_sizes[i + 1], layer_sizes[i])) for i in range(len(layer_sizes) - 1)])
    for ind, w in enumerate(self.encode_w):
      weight_init.xavier_uniform(w)

    self.encode_b = nn.ParameterList(
      [nn.Parameter(torch.zeros(layer_sizes[i + 1])) for i in range(len(layer_sizes) - 1)])

    reversed_enc_layers = list(reversed(layer_sizes))

    self.is_constrained = is_constrained
    if not is_constrained:
      self.decode_w = nn.ParameterList(
      [nn.Parameter(torch.rand(reversed_enc_layers[i + 1], reversed_enc_layers[i])) for i in range(len(reversed_enc_layers) - 1)])
      for ind, w in enumerate(self.decode_w):
        weight_init.xavier_uniform(w)
    else:
      self.decode_w = list(reversed(self.encode_w))
      for ind, w in enumerate(self.decode_w):
        self.decode_w[ind] = w.transpose(0,1)

    self.decode_b = nn.ParameterList(
      [nn.Parameter(torch.zeros(reversed_enc_layers[i + 1])) for i in range(len(reversed_enc_layers) - 1)])

    print("******************************")
    print("******************************")
    print(layer_sizes)
    print("Dropout drop probability: {}".format(self._dp_drop_prob))
    print("Encoder pass:")
    for ind, w in enumerate(self.encode_w):
      print(w.data.size())
      print(self.encode_b[ind].size())
    print("Decoder pass:")
    if self.is_constrained:
      print('Decoder is constrained')
      for ind, w in enumerate(list(reversed(self.encode_w))):
        print(w.transpose(0, 1).size())
        print(self.decode_b[ind].size())
    else:
      for ind, w in enumerate(self.decode_w):
        print(w.data.size())
        print(self.decode_b[ind].size())
    print("******************************")
    print("******************************")


  def encode(self, x):
    for ind, w in enumerate(self.encode_w):
      x = activation(input=F.linear(input=x, weight=w, bias=self.encode_b[ind]), kind=self._nl_type)
    if self._dp_drop_prob > 0: # apply dropout only on code layer
      x = self.drop(x)
    return x

  def decode(self, z):
    for ind, w in enumerate(self.decode_w):
      z = activation(input=F.linear(input=z, weight=w, bias=self.decode_b[ind]),
                  # last layer or decoder should not apply non linearities
                  kind=self._nl_type if ind!=self._last else 'none')
      #if self._dp_drop_prob > 0 and ind!=self._last: # and no dp on last layer
      #  z = self.drop(z)
    return z

  def forward(self, x):
    return self.decode(self.encode(x))

