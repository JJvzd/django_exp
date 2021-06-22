from django import forms

from clients.models.agents import Agent


class AgentBankAccountForm(forms.ModelForm):

    # def __init__(self, *args, **kwargs):
    #     super(AgentBankAccountForm, self).__init__(*args, **kwargs)
    #     for field in self.fields:
    #         print(self.fields[field])
    #         self.fields[field].required = True

    class Meta:
        model = Agent
        fields = {
            'bank_account_bik',
            'bank_account_bank',
            'bank_account_checking_account',
            'bank_account_correspondent_account'
        }

