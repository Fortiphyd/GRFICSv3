from app.utility.base_object import BaseObject


class Human(BaseObject):

    @property
    def display(self):
        return self.clean(dict(name=self.name, platform=self.platform, task_interval=self.task_interval,
                               task_cluster_interval=self.task_cluster_interval, tasks_per_cluster=self.tasks_per_cluster,
                               extra=self.extra, workflows=[w.display for w in self.workflows]))

    @property
    def unique(self):
        return self.hash('%s' % self.name)

    def __init__(self, name, platform, task_interval, task_cluster_interval, tasks_per_cluster, extra, workflows):
        super().__init__()
        self.name = name
        self.platform = platform
        self.task_interval = task_interval
        self.task_cluster_interval = task_cluster_interval
        self.tasks_per_cluster = tasks_per_cluster
        self.extra = extra
        self.workflows = workflows

    def store(self, ram):
        existing = self.retrieve(ram['humans'], self.unique)
        if not existing:
            ram['humans'].append(self)
            return self.retrieve(ram['humans'], self.unique)
        return existing
