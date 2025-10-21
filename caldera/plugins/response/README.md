# Response

A MITRE Caldera plugin for doing autonomous incident response.

Please note: the config file for this plugin, `conf/response.yml`, contains a field called `auto_operation_enable`. 
Setting this value to `True` (the default value is `False`) will cause Caldera to automatically create and run Blue 
Response operations in responses to Red operations. Previously, the behavior specified by `True` was the default 
behavior for this plugin, but this had been changed due to potential user confusion.
