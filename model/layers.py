# coding: utf-8


<<<<<<< HEAD
=======
import math
>>>>>>> 61e71b107d0898998826762cc4c16efa40fb733e
import numpy as np
import torch


def split_layer(output_ch, chunks):
    split = [np.int(np.ceil(output_ch / chunks)) for _ in range(chunks)]
    split[chunks - 1] += output_ch - sum(split)
    return split


def swish(x):
    return x * torch.sigmoid(x)


def mish(x):
    return x * torch.tanh(torch.nn.functional.softplus(x))


# def leaky_relu(x, gamma=.2):
#     return x if x >= 0 else -gamma * x


class Swish(torch.nn.Module):

    def forward(self, x):
        return swish(x)


class Mish(torch.nn.Module):

    def forward(self, x):
        return mish(x)


class Conv_Block(torch.nn.Module):

    def __init__(self, input_ch, output_ch, kernel_size, stride, padding, norm=True):
        super(Conv_Block, self).__init__()
        layer = []
        layer.append(torch.nn.Conv2d(input_ch, output_ch,
                                     kernel_size=kernel_size, stride=stride,
                                     padding=padding))
        if norm is True:
            layer.append(torch.nn.BatchNorm2d(output_ch))
        # layer.append(torch.nn.ReLU())
        self.layer = torch.nn.Sequential(*layer)

    def forward(self, x):
        return torch.nn.functional.relu(self.layer(x))


class D_Conv_Block(torch.nn.Module):

    def __init__(self, input_ch, output_ch, norm=True):
        super(D_Conv_Block, self).__init__()
        layer = [torch.nn.ConvTranspose2d(
            input_ch, output_ch, kernel_size=2, stride=2)]
        if norm is True:
            layer.append(torch.nn.BatchNorm2d(output_ch))
        layer.append(torch.nn.ReLU())
        self.layer = torch.nn.Sequential(*layer)

    def forward(self, x):
        return self.layer(x)


class SA_Block(torch.nn.Module):

    def __init__(self, input_ch):
        super(SA_Block, self).__init__()
        self.theta = torch.nn.Conv2d(input_ch, input_ch // 8, 1, 1, 0)
        self.phi = torch.nn.Conv2d(input_ch, input_ch // 8, 1, 1, 0)
        self.g = torch.nn.Conv2d(input_ch, input_ch, 1, 1, 0)
        # self.attn = torch.nn.Conv2d(input_ch // 2, input_ch, 1, 1, 0)
        self.sigma_ratio = torch.nn.Parameter(
            torch.zeros(1), requires_grad=True)

    def forward(self, x):
        batch_size, ch, h, w = x.size()
        # theta path (first conv block)
        theta = self.theta(x)
        theta = theta.view(batch_size, ch // 8, h * w).permute((0, 2, 1))  # (bs, HW, CH // 8)
        # phi path (second conv block)
        phi = self.phi(x)
        phi = torch.nn.functional.max_pool2d(phi, 2)
        phi = phi.view(batch_size, ch // 8, h * w // 4)  # (bs, CH // 8, HW)
        # attention path (theta and phi)
        attn = torch.bmm(theta, phi)  # (bs, HW, HW // 4)
        attn = torch.nn.functional.softmax(attn, dim=-1)
        # g path (third conv block)
        g = self.g(x)
        g = torch.nn.functional.max_pool2d(g, 2)
        # (bs, HW // 4, CH)
        g = g.view(batch_size, ch, h * w // 4).permute((0, 2, 1))
        # attention map (g and attention path)
        attn_g = torch.bmm(attn, g)  # (bs, HW, CH)
        attn_g = attn_g.permute((0, 2, 1)).view(
            batch_size, ch, h, w)  # (bs, CH, H, W)
        return x + self.sigma_ratio * attn_g


class DW_PT_Conv(torch.nn.Module):

    def __init__(self, input_ch, output_ch, kernel_size, activation='relu'):
        super(DW_PT_Conv, self).__init__()
        self.activation = activation
        self.depth = torch.nn.Conv2d(input_ch, input_ch, kernel_size, 1, 1, groups=input_ch)
        self.point = torch.nn.Conv2d(input_ch, output_ch, 1, 1, 0)

    def _activation_fn(self, x):
        if self.activation == 'relu':
            return torch.relu(x)
        elif self.activation == 'swish':
            return swish(x)
        elif self.activation == 'mish':
            return mish(x)
        else:
            return x

    def forward(self, x):
        x = self.depth(x)
        x = self._activation_fn(x)
        x = self.point(x)
        x = self._activation_fn(x)
        return x


class HSI_prior_block(torch.nn.Module):

    def __init__(self, input_ch, output_ch, feature=64, activation='relu'):
        super(HSI_prior_block, self).__init__()
        self.activation = activation
        self.spatial_1 = torch.nn.Conv2d(input_ch, feature, 3, 1, 1)
        self.spatial_2 = torch.nn.Conv2d(feature, output_ch, 3, 1, 1)
        self.spectral = torch.nn.Conv2d(output_ch, input_ch, 1, 1, 0)

    def _activation_fn(self, x):
        if self.activation == 'relu':
            return torch.relu(x)
        elif self.activation == 'swish':
            return swish(x)
        elif self.activation == 'mish':
            return mish(x)
        else:
            return x

    def forward(self, x):
        x_in = x
        h = self.spatial_1(x)
        h = self._activation_fn(h)
        h = self.spatial_2(h)
        x = h + x_in
        x = self.spectral(x)
        return x


class My_HSI_network(torch.nn.Module):

    def __init__(self, input_ch, output_ch, feature=64, activation='relu'):
        super(My_HSI_network, self).__init__()
        self.activation = activation
        self.spatial_1 = DW_PT_Conv(input_ch, feature, 3, activation=None)
        self.spatial_2 = DW_PT_Conv(feature, output_ch, 3, activation=None)
        self.spectral = torch.nn.Conv2d(output_ch, output_ch, 1, 1, 0)

    def _activation_fn(self, x):
        if self.activation == 'relu':
            return torch.relu(x)
        elif self.activation == 'swish':
            return swish(x)
        elif self.activation == 'mish':
            return mish(x)
        else:
            return x

    def forward(self, x):
        x_in = x
        h = self.spatial_1(x)
        h = self._activation_fn(h)
        h = self.spatial_2(h)
        x = h + x_in
        x = self.spectral(x)
        return x


class RAM(torch.nn.Module):

    def __init__(self, input_ch, output_ch, ratio=None, **kwargs):
        super(RAM, self).__init__()

        if ratio is None:
            self.ratio = 2
        else:
            self.ratio = ratio
        self.activation = kwargs.get('attn_activation')
        self.spatial_attn = torch.nn.Conv2d(input_ch, output_ch, 3, 1, 1, groups=input_ch)
        self.spectral_pooling = GVP()
        self.spectral_Linear = torch.nn.Linear(input_ch, input_ch // self.ratio)
        self.spectral_attn = torch.nn.Linear(input_ch // self.ratio, output_ch)

    def _activation_fn(self, x):
        if self.activation == 'relu':
            return torch.relu(x)
        if self.activation == 'swish':
            return swish(x)
        elif self.activation == 'mish':
            return mish(x)
        elif self.activation == 'leaky' or self.activation == 'leaky_relu':
            return torch.nn.functional.leaky_relu(x)
        else:
            return x

    def forward(self, x):
        batch_size, ch, h, w = x.size()
        spatial_attn = self._activation_fn(self.spatial_attn(x))
        spectral_pooling = self.spectral_pooling(x).view(-1, ch)
        spectral_linear = torch.relu(self.spectral_Linear(spectral_pooling))
        spectral_attn = self.spectral_attn(spectral_linear).unsqueeze(-1).unsqueeze(-1)

        # attn_output = torch.sigmoid(spatial_attn + spectral_attn + spectral_pooling.unsqueeze(-1).unsqueeze(-1))
        attn_output = torch.sigmoid(spatial_attn * spectral_attn)
        output = attn_output * x
        return output


class Global_Average_Pooling2d(torch.nn.Module):

    def forward(self, x):
        bs, ch, h, w = x.size()
        return torch.nn.functional.avg_pool2d(x, kernel_size=(h, w)).view(-1, ch)


class GVP(torch.nn.Module):

    def forward(self, x):
        batch_size, ch, h, w = x.size()
        avg_x = torch.nn.functional.avg_pool2d(x, kernel_size=(h, w))
        var_x = torch.nn.functional.avg_pool2d((x - avg_x) ** 2, kernel_size=(h, w))
        return var_x.view(-1, ch)


class SE_block(torch.nn.Module):

    def __init__(self, input_ch, output_ch, **kwargs):
        super(SE_block, self).__init__()
        if 'ratio' in kwargs:
            ratio = kwargs['ratio']
        else:
            ratio = 2
        mode = kwargs.get('mode')
        if mode == 'GVP':
            self.pooling = GVP()
        else:
            self.pooling = Global_Average_Pooling2d()
        self.squeeze = torch.nn.Linear(input_ch, output_ch // ratio)
        self.extention = torch.nn.Linear(output_ch // ratio, output_ch)

    def forward(self, x):
        gap = self.pooling(x)
        squeeze = torch.relu(self.squeeze(gap))
        attn = torch.sigmoid(self.extention(squeeze))
        return x * attn.unsqueeze(-1).unsqueeze(-1)


class Attention_HSI_prior_block(torch.nn.Module):

    def __init__(self, input_ch, output_ch, feature=64, **kwargs):
        super(Attention_HSI_prior_block, self).__init__()
        self.mode = kwargs.get('mode')
        ratio = kwargs.get('ratio')
        if ratio is None:
            ratio = 2
        attn_activation = kwargs.get('attn_activation')
        self.spatial_1 = torch.nn.Conv2d(input_ch, feature, 3, 1, 1)
        self.spatial_2 = torch.nn.Conv2d(feature, output_ch, 3, 1, 1)
        self.attention = RAM(output_ch, output_ch, ratio=ratio, attn_activation=attn_activation)
        self.spectral = torch.nn.Conv2d(output_ch, output_ch, 1, 1, 0)
        if self.mode is not None:
            self.spectral_attention = SE_block(output_ch, output_ch, mode=self.mode, ratio=ratio)
        self.activation = kwargs.get('activation')

    def _activation_fn(self, x):
        if self.activation == 'swish':
            return swish(x)
        elif self.activation == 'mish':
            return mish(x)
        elif self.activation == 'leaky' or self.activation == 'leaky_relu':
            return torch.nn.functional.leaky_relu(x)
        else:
            return torch.relu(x)

    def forward(self, x):
        x_in = x
        h = self._activation_fn(self.spatial_1(x))
        h = self.spatial_2(h)
        h = self.attention(h)
        x = h + x_in
        x = self.spectral(x)
        if self.mode is not None:
            x = self.spectral_attention(x)
        return x


class Ghost_layer(torch.nn.Module):

    def __init__(self, input_ch, output_ch, *args, kernel_size=1, stride=1, dw_kernel=3, dw_stride=1, ratio=2, **kwargs):
        super(Ghost_layer, self).__init__()
        self.output_ch = output_ch
        primary_ch = math.ceil(output_ch / ratio)
        new_ch = output_ch * (ratio - 1)
        self.activation = kwargs.get('activation')
        self.primary_conv = torch.nn.Conv2d(input_ch, primary_ch, kernel_size, stride, padding=kernel_size // 2)
        self.cheep_conv = torch.nn.Conv2d(primary_ch, new_ch, dw_kernel, dw_stride, padding=dw_kernel // 2, groups=primary_ch)

    def _activation_fn(self, x):
        if self.activation == 'swish':
            return swish(x)
        elif self.activation == 'mish':
            return mish(x)
        elif self.activation == 'leaky' or self.activation == 'leaky_relu':
            return torch.nn.functional.leaky_relu(x)
        elif self.activation == 'relu':
            return torch.relu(x)
        else:
            return x

    def forward(self, x):
        primary_x = self._activation_fn(self.primary_conv(x))
        new_x = self._activation_fn(self.cheep_conv(primary_x))
        output = torch.cat([primary_x, new_x], dim=1)
        return output[:, :self.output_ch, :, :]


class Ghost_Bottleneck(torch.nn.Module):

    def __init__(self, input_ch, hidden_ch, output_ch, *args, kernel_size=1, stride=1, se_flag=True, **kwargs):
        super(Ghost_Bottleneck, self).__init__()

        activation = kwargs.get('activation')
        dw_kernel = kwargs.get('dw_kernel')
        dw_stride = kwargs.get('dw_stride')
        ratio = kwargs.get('ratio')

        Ghost_layer1 = Ghost_layer(input_ch, hidden_ch, kernel_size=1, activation=activation)
        depth = torch.nn.Conv2d(hidden_ch, hidden_ch, kernel_size, stride, groups=hidden_ch) if stride == 2 else torch.nn.Sequential()
        se_block = SE_block(hidden_ch, hidden_ch, ratio=8) if se_flag is True else torch.nn.Sequential()
        Ghost_layer2 = Ghost_layer(hidden_ch, output_ch, kernel_size=kernel_size, activation=activation)
        self.ghost_layer = torch.nn.Sequential(Ghost_layer1, depth, se_block, Ghost_layer2)

        if stride == 1 and input_ch == output_ch:
            self.shortcut = torch.nn.Sequential()
        else:
            self.shortcut = torch.nn.Sequential(
                    torch.nn.Conv2d(input_ch, input_ch, kernel_size, stride=1, padding=kernel_size // 2, groups=input_ch),
                    torch.nn.Conv2d(input_ch, output_ch, 1, 1, 0)
            )

    def forward(self, x):
        h = self.shortcut(x)
        x = self.ghost_layer(x)
        return x + h
