Doctor (``qkdsec.doctor``)
==========================

.. automodule:: qkdsec.doctor

Probe results
-------------

.. autoclass:: qkdsec.doctor.ProbeResult
   :members:

.. autoclass:: qkdsec.doctor.ProbeStatus
   :members:

.. autoclass:: qkdsec.doctor.Report
   :members:

Probes
------

.. autofunction:: qkdsec.doctor.run_all

.. automodule:: qkdsec.doctor.probes
   :members:
   :exclude-members: ProbeResult, ProbeStatus, Report, run_all

Formatters
----------

.. autofunction:: qkdsec.doctor.format_text

.. autofunction:: qkdsec.doctor.format_json

.. autofunction:: qkdsec.doctor.format_html
