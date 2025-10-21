import json
import logging

from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):
    """
    This parser extracts information from sysmon events that
     have been transformed via the Elastic Common Schema (ECS)
    JSON documents (REF: https://www.elastic.co/guide/en/ecs/current/ecs-field-reference.html).
    """

    logger = logging.getLogger("ecs_parser")

    def parse(self, blob):
        relationships = []
        loaded = json.loads(blob)

        # Do not parse facts if the result is an array (multiple results returned).
        # This prevents facts from being parsed when results are directly returned from elasticat,
        # allowing them to be parsed and added to pseudo-links created for the results.  This
        # restriction is present because a fact can not exist on more than one link in an operation at
        # a time.
        if isinstance(loaded, dict):
            event = loaded
            for mp in self.mappers:
                try:
                    match = self.parse_options[mp.target.split('.').pop()](event)
                    if match:
                        guid = self.parse_process_guid(event)
                        relationships.append(Relationship(source=Fact(mp.source, guid),
                                                          edge=mp.edge,
                                                          target=Fact(mp.target, match)))
                except Exception as e:
                    self.logger.debug('Problem with mapper: %s - %s ' % (mp, e), exc_info=True)

            relationships.extend(self.parse_elasticsearch_results(event))

        return relationships

    @property
    def parse_options(self):
        return dict(
            eventid=self.parse_eventid,
            recordid=self.parse_recordid,
            user=self.parse_user,
            guid=self.parse_process_guid,
            pid=self.parse_pid,
            name=self.parse_process_name,
            parent_guid=self.parse_parent_process_guid,
        )

    @classmethod
    def parse_elasticsearch_results(cls, event):
        elasticsearch_id = event['_id']
        relationships = []
        for k, v in cls.flatten_dict(event["_source"]).items():
            try:
                relationships.append(
                    Relationship(
                        source=Fact(trait='elasticsearch.result.id', value=elasticsearch_id),
                        target=Fact(trait=cls._sanitize_fact_traits(k), value=v if isinstance(v, str) else json.dumps(v)),
                        edge='has_property'
                    )
                )
            except Exception as e:
                cls.logger.debug(e, exc_info=True)
        pid = cls.parse_pid(event)
        if pid:
            relationships.append(
                Relationship(
                    source=Fact(trait='host.process.id', value=pid),
                    edge=None,
                    target=Fact(trait=None, value=None)
                )
            )
        return relationships

    @staticmethod
    def parse_process_guid(event):
        return event['_source']['process']['entity_id'].strip('{').strip('}')

    @staticmethod
    def parse_parent_process_guid(event):
        return event['_source']['process']['parent']['entity_id'].strip('{').strip('}')

    @staticmethod
    def parse_eventid(event):
        return event['_source']['winlog']['event_id']

    @staticmethod
    def parse_recordid(event):
        return event['_source']['winlog']['record_id']

    @staticmethod
    def parse_user(event):
        return '%s\\%s' % (event['_source']['user']['domain'], event['_source']['user']['name'])

    @staticmethod
    def parse_pid(event):
        return event.get('_source', {}).get('process', {}).get('pid')

    @staticmethod
    def parse_process_name(event):
        return event['_source']['process']['name']

    @staticmethod
    def flatten_dict(dict_obj):
        new = {}

        def _flatten(obj, parent="", sep="."):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    next_parent = parent + sep + str(k) if parent else k
                    _flatten(v, parent=next_parent)
            else:
                new[parent] = obj
        _flatten(dict_obj)
        return new

    @staticmethod
    def _sanitize_fact_traits(trait):
        special_chars = ('@', '"', '"', '[', ']', '\\', '/')
        for c in special_chars:
            trait = trait.replace(c, '')
        return trait
