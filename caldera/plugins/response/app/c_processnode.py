import marshmallow as ma

from app.utility.base_object import BaseObject
from app.objects.secondclass.c_link import LinkSchema


class ProcessNodeSchema(ma.Schema):
    pid = ma.fields.Integer()
    link = ma.fields.Nested(LinkSchema())
    parent_guid = ma.fields.String()
    child_guids = ma.fields.List(ma.fields.String())

    @ma.post_load()
    def build_pidnode(self, data, **_):
        return ProcessNode(**data)


class ProcessNode(BaseObject):
    """
    ProcessNodes are used within ProcessTrees to represent processes and their parent/child relationships.
    """

    def __init__(self, pid, link, parent_guid=None, child_guids=None):
        super().__init__()
        self.pid = pid
        self.link = link
        self.parent_guid = parent_guid
        self.child_guids = child_guids if child_guids else []

    def add_child(self, child_guid, child_link):
        if self.link.host == child_link.host and child_guid not in self.child_guids:
            self.child_guids.append(child_guid)
