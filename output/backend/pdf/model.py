"""
training/classify/model.py — 1D CNN (ResNet-style) untuk klasifikasi EKG 12-lead
-> 5 superclass (multi-label). Input (B,12,1000) -> output logits (B,5).
"""
import torch
import torch.nn as nn


class ResBlock1d(nn.Module):
    def __init__(self, cin, cout, stride=1):
        super().__init__()
        self.c1 = nn.Conv1d(cin, cout, 7, stride=stride, padding=3, bias=False)
        self.b1 = nn.BatchNorm1d(cout)
        self.c2 = nn.Conv1d(cout, cout, 7, padding=3, bias=False)
        self.b2 = nn.BatchNorm1d(cout)
        self.act = nn.ReLU(inplace=True)
        self.drop = nn.Dropout(0.2)
        self.short = (nn.Sequential() if (stride == 1 and cin == cout)
                      else nn.Sequential(nn.Conv1d(cin, cout, 1, stride=stride,
                                                   bias=False),
                                         nn.BatchNorm1d(cout)))

    def forward(self, x):
        r = self.short(x)
        x = self.act(self.b1(self.c1(x)))
        x = self.drop(x)
        x = self.b2(self.c2(x))
        return self.act(x + r)


class ECGNet(nn.Module):
    def __init__(self, n_leads=12, n_classes=5, base=32):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv1d(n_leads, base, 15, stride=2, padding=7, bias=False),
            nn.BatchNorm1d(base), nn.ReLU(inplace=True))
        self.layers = nn.Sequential(
            ResBlock1d(base, base, 1),
            ResBlock1d(base, base * 2, 2),
            ResBlock1d(base * 2, base * 2, 1),
            ResBlock1d(base * 2, base * 4, 2),
            ResBlock1d(base * 4, base * 4, 1),
            ResBlock1d(base * 4, base * 8, 2),
        )
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool1d(1), nn.Flatten(),
            nn.Dropout(0.3), nn.Linear(base * 8, n_classes))

    def forward(self, x):
        return self.head(self.layers(self.stem(x)))


if __name__ == '__main__':
    m = ECGNet()
    x = torch.randn(2, 12, 1000)
    print('params:', sum(p.numel() for p in m.parameters()))
    print('out:', m(x).shape)
