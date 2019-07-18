import torch.nn
from sample.base.base_model import BaseModel



class MLP_from_Latent(BaseModel):
    def __init__(self, d_in, d_hidden=2048, d_out=51, n_hidden=2, dropout=0.5):
        super().__init__()
        self.dropout = dropout
        if n_hidden == 0:
            self.fully_connected = torch.nn.Linear(d_in, d_out)
        else:
            module_list = [torch.nn.Linear(d_in, d_hidden),
                           torch.nn.ReLU(),
                           torch.nn.BatchNorm1d(d_hidden, affine=True)]

            for i in range(n_hidden - 1):
                module_list.extend([
                    torch.nn.Dropout(inplace=True, p=self.dropout),
                    torch.nn.Linear(d_hidden, d_hidden),
                    torch.nn.ReLU(),
                    torch.nn.BatchNorm1d(d_hidden, affine=True),
                    torch.nn.Dropout(inplace=True, p=self.dropout)]
                )
            module_list.append(torch.nn.Linear(d_hidden, d_out))

            self.fully_connected = torch.nn.Sequential(*module_list)

    def forward(self, inputs):
        input_latent = inputs['L_3d']
        batch_size = input_latent.size()[0]
        input_flat = input_latent.view(batch_size, -1)
        output = self.fully_connected(input_flat)
        return output