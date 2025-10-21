import marshmallow as ma
from random import randint

from app.utility.base_object import BaseObject
from app.objects.interfaces.i_object import FirstClassObjectInterface
from plugins.response.app.c_processnode import ProcessNode, ProcessNodeSchema


class ProcessTreeSchema(ma.Schema):
    id = ma.fields.Integer()
    pid_to_guids_map = ma.fields.Dict(keys=ma.fields.Integer(), values=ma.fields.List(ma.fields.String()))
    guid_to_processnode_map = ma.fields.Dict(keys=ma.fields.String(), values=ma.fields.Nested(ProcessNodeSchema()))

    @ma.post_load()
    def build_processtree(self, data, **_):
        return ProcessTree(**data)


class ProcessTree(FirstClassObjectInterface, BaseObject):
    """
    This data structure is used to track child processes of abilities run by the red team.
    Each ProcessTree is unique to a host to ensure that processes aren't being incorrectly linked across hosts.
    As Windows allows the reuse of PIDs, processes are uniquely identified within the ProcessTree using the matching
    Sysmon GUID for the process.
    """

    schema = ProcessTreeSchema()

    @property
    def unique(self):
        return self.host + str(self.ptree_id)

    def __init__(self, host, ptree_id=None, pid_to_guids_map=None, guid_to_processnode_map=None):
        super().__init__()
        self.ptree_id = ptree_id if ptree_id else randint(0, 999999)
        self.host = host
        self.pid_to_guids_map = pid_to_guids_map if pid_to_guids_map else dict()
        self.guid_to_processnode_map = guid_to_processnode_map if guid_to_processnode_map else dict()

    async def add_processnode(self, guid, pid, link, parent_guid=None):
        """
        ProcessNodes are used to represent processes and their parent/child relationships.
        When the Child Process Ability is run and produces a process as a result, the process is added as a ProcessNode,
        and the parent/child relationships of that ProcessNode and related ProcessNodes are updated accordingly.
        """
        processnode = ProcessNode(pid=pid, link=link, parent_guid=parent_guid)
        self.guid_to_processnode_map[guid] = processnode

        if pid in self.pid_to_guids_map:
            self.pid_to_guids_map[pid].append(guid)
        else:
            self.pid_to_guids_map[pid] = [guid]

        if parent_guid:
            self.guid_to_processnode_map[parent_guid].add_child(guid, link)

    async def find_original_processes_by_pid(self, pid):
        """
        This method takes in a PID and returns the top-level (parent-most/eldest/original) PID.
        As Windows allows for PIDs to be repeated, this method may return multiple top-level PIDs.
        In the case of multiple PIDs being returned, it is up to the caller/user to determine which of the returned PIDs
        is the desired one.
        """
        original_guids = []
        if pid in self.pid_to_guids_map:
            guids = self.pid_to_guids_map[pid]
            for guid in guids:
                original_guid = guid
                parent_guid = await self.find_parent_guid(original_guid)
                while parent_guid is not None:
                    original_guid = parent_guid
                    parent_guid = await self.find_parent_guid(original_guid)
                original_guids.append(original_guid)
        return await self.convert_guids_to_pids(original_guids)

    async def find_parent_guid(self, guid):
        if guid in self.guid_to_processnode_map:
            return self.guid_to_processnode_map[guid].parent_guid
        return None

    async def convert_guids_to_pids(self, guids):
        pids = []
        for guid in guids:
            for pid in self.pid_to_guids_map:
                if guid in self.pid_to_guids_map[pid]:
                    pids.append(pid)
        return pids

    def store(self, ram):
        existing = self.retrieve(ram['processtrees'], self.unique)
        if not existing:
            ram['processtrees'].append(self)
            return self.retrieve(ram['processtrees'], self.unique)
        return existing
