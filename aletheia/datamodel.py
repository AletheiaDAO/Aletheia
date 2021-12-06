from typing_extensions import Required
from mongoengine import connect, Document, StringField, DictField, ListField, DateTimeField, NumberField
import datetime
import copy

from settings import MONGO_DB, MONGO_HOST, MONGO_PORT


connect(alias='cascad', db=MONGO_DB, host=MONGO_HOST, port=MONGO_PORT)


class AgentModel(Document):
    unique_id = StringField(required=True, unique=True, primary_key=True)
    step = NumberField()
    creation_date = DateTimeField()
    modified_date = DateTimeField(default=datetime.datetime.now)
    state = DictField()
    state_history = ListField(DictField, default=list)

    def save(self, *args, **kwargs):
        if not self.creation_date:
            self.creation_date = datetime.datetime.now()

        tmp_state = copy.deepcopy(self.state)
        ## add the step infor
        tmp_state['step'] = self.step
        self.state_history.append(tmp_state)
        
        self.modified_date = datetime.datetime.now()
        return super(AgentModel, self).save(*args, **kwargs)
