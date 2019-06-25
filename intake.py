from flask_sqlalchemy import Model
from sqlalchemy.orm import validates
from sqlalchemy import *
from wtforms_alchemy import ModelForm
from wtforms.validators import Email

class Client(Model):
    __tablename__ = 'clients_notes'
    id = Column(Integer, primary_key=True)
    fjc = Column(Enum('brooklyn', 'queens', 'the bronx', 'manhattan', 'staten island'),  
            nullable=False,
            info={'label': 'FJC'})
    consultant_initials = Column(String(100), nullable=False,
            info={'label': 'Consultant Initials'})
    referring_professional = Column(String(100), nullable=False,
            info={'label': 'Name of Referring Professional'})
    referring_professional_email = Column(String(255), nullable=True,
            info={'label': 'Email of Referring Professional (Optional)', 'validators':Email()})
    """
    id = sa.Column(sa.Integer, primary_key=True)
    fjc = sa.Column(sa.Enum('brooklyn', 'queens', 'the bronx', 'manhattan', 'staten island'), 
            nullable=False,
            info={'label': 'FJC'})
    consultant_initials = sa.Column(sa.String(100), nullable=False,
            info={'label': 'Consultant Initials'})
    referring_professional = sa.Column(sa.String(100), nullable=False,
            info={'label': 'Name of Referring Professional'})
    referring_professional_email = sa.Column(sa.String(255), nullable=True,
            info={'label': 'Email of Referring Professional (Optional)', 'validators':Email()})
    #referring_professional = sa.C
    """


    #@validates('fjc')
    #def validate_fjc(self, key, data):
    #    assert data in ['brooklyn', 'queens', 'the bronx', 'manhattan', 'staten island']
    #    return data

    def __repr__(self):
        return 'client {}'.format(self.fjc)

class ClientForm(ModelForm):
    class Meta:
        model = Client
