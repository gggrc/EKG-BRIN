"""
training/unet.py — Arsitektur U-Net untuk segmentasi trace EKG.

Input  : gambar kertas-EKG (1 channel grayscale, HxW)
Output : peta probabilitas trace (1 channel, HxW) -> 1 = piksel garis EKG

U-Net klasik (Ronneberger 2015) versi ringkas: encoder-decoder dengan
skip-connection. Cukup ringan untuk RTX 3060 (6 GB).
"""

import torch
import torch.nn as nn


class DoubleConv(nn.Module):
    """(Conv -> BN -> ReLU) x2."""

    def __init__(self, cin, cout):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(cin, cout, 3, padding=1, bias=False),
            nn.BatchNorm2d(cout),
            nn.ReLU(inplace=True),
            nn.Conv2d(cout, cout, 3, padding=1, bias=False),
            nn.BatchNorm2d(cout),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.net(x)


class UNet(nn.Module):
    def __init__(self, in_ch=1, out_ch=1, base=32):
        super().__init__()
        b = base
        self.d1 = DoubleConv(in_ch, b)
        self.d2 = DoubleConv(b, b * 2)
        self.d3 = DoubleConv(b * 2, b * 4)
        self.d4 = DoubleConv(b * 4, b * 8)
        self.pool = nn.MaxPool2d(2)
        self.bott = DoubleConv(b * 8, b * 16)

        self.up4 = nn.ConvTranspose2d(b * 16, b * 8, 2, stride=2)
        self.u4 = DoubleConv(b * 16, b * 8)
        self.up3 = nn.ConvTranspose2d(b * 8, b * 4, 2, stride=2)
        self.u3 = DoubleConv(b * 8, b * 4)
        self.up2 = nn.ConvTranspose2d(b * 4, b * 2, 2, stride=2)
        self.u2 = DoubleConv(b * 4, b * 2)
        self.up1 = nn.ConvTranspose2d(b * 2, b, 2, stride=2)
        self.u1 = DoubleConv(b * 2, b)

        self.outc = nn.Conv2d(b, out_ch, 1)

    @staticmethod
    def _crop_cat(up, skip):
        """Samakan ukuran (untuk H/W yang tidak kelipatan 16) lalu concat."""
        if up.shape[-2:] != skip.shape[-2:]:
            up = nn.functional.interpolate(
                up, size=skip.shape[-2:], mode="bilinear", align_corners=False)
        return torch.cat([skip, up], dim=1)

    def forward(self, x):
        c1 = self.d1(x)
        c2 = self.d2(self.pool(c1))
        c3 = self.d3(self.pool(c2))
        c4 = self.d4(self.pool(c3))
        bn = self.bott(self.pool(c4))

        x = self.u4(self._crop_cat(self.up4(bn), c4))
        x = self.u3(self._crop_cat(self.up3(x), c3))
        x = self.u2(self._crop_cat(self.up2(x), c2))
        x = self.u1(self._crop_cat(self.up1(x), c1))
        return self.outc(x)  # logits (tanpa sigmoid)


if __name__ == "__main__":
    net = UNet()
    n = sum(p.numel() for p in net.parameters())
    x = torch.randn(1, 1, 256, 256)
    print("params:", n)
    print("out:", net(x).shape)
