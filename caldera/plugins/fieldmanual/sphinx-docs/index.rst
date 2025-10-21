.. caldera documentation master file

.. |TM| unicode:: U+2122
   :ltrim:

Welcome to MITRE Caldera's documentation!
=========================================

Caldera |TM| is an adversary emulation platform designed to easily run autonomous breach-and-attack simulation exercises. It can also
be used to run manual red-team engagements or automated incident response. Caldera is built on the
`MITRE ATT&CK <https://attack.mitre.org>`_ |TM| framework and is an active research project at MITRE.

The framework consists of two components:

1. **The core system**. This is the framework code, including an asynchronous
command-and-control (C2) server with a REST API and a web interface.

2. **Plugins**. These are separate repositories that hang off of the core framework, providing additional
functionality. Examples include agents, GUI interfaces, collections of TTPs and more.

Visit `Installing Caldera <Installing-Caldera.html>`_ for installation information.

For getting familiar with the project, visit `Getting started <Getting-started.html>`_, which documents step-by-step
guides for the most common use cases of Caldera, and `Basic usage <Basic-Usage.html>`_, which documents how to use
some of the basic components in core Caldera. Visit `Learning the terminology <Learning-the-terminology.html>`_ for
in depth definitions of the terms used throughout the project.

For information about Caldera plugins, visit `Plugin Library <Plugin-library.html>`_ and
`How to Build Plugins <How-to-Build-Plugins.html>`_ if you are interested in building your own.

.. toctree::
   :maxdepth: 2
   :caption: Usage Guides

   Installing-Caldera.md
   Getting-started.md
   Learning-the-terminology.md
   Basic-Usage.md
   Server-Configuration.md
   Plugin-library.md
   Parsers.md
   Relationships.md
   Requirements.md
   Objectives.md
   Operation-Results.md
   Initial-Access-Attacks.md
   Lateral-Movement-Guide.md
   Dynamically-Compiled-Payloads.md
   Exfiltration.md
   Sandcat-Peer-to-Peer.md
   C2-Tunneling.md
   Uninstalling-Caldera.md
   Troubleshooting.md
   resources

The following section contains documentation from installed plugins.

.. toctree::
   :maxdepth: 3
   :caption: Plugin Documentation
   :glob:

   plugins/**/*


The following section contains information intended to help developers
understand the inner workings of the Caldera adversary emulation tool, Caldera
plugins, or new tools that interface with the Caldera server.

.. toctree::
   :maxdepth: 2
   :caption: Developer Information

   The-REST-API.md
   How-to-Build-Plugins.md
   How-to-Build-Planners.md
   How-to-Build-Agents.md

.. toctree::
   :maxdepth: 3
   :caption: Core System API
   :glob:

   _generated/*


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`