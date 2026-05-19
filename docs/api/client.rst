ETSI 014 client (``qkdsec.client``)
===================================

.. automodule:: qkdsec.client
   :members:
   :exclude-members: KeyResponse, KeysContainer, StatusResponse, ETSI014Client, KMEError, KMEHTTPError, KMENotFoundError

Synchronous client
------------------

.. autoclass:: qkdsec.client.ETSI014Client
   :members:
   :show-inheritance:

Asynchronous client
-------------------

.. autoclass:: qkdsec.client.aio.AsyncETSI014Client
   :members:
   :show-inheritance:

Response types
--------------

.. autoclass:: qkdsec.client.KeyResponse
   :members:

.. autoclass:: qkdsec.client.KeysContainer
   :members:

.. autoclass:: qkdsec.client.StatusResponse
   :members:

Errors
------

.. autoexception:: qkdsec.client.KMEError

.. autoexception:: qkdsec.client.KMEHTTPError
   :members:

.. autoexception:: qkdsec.client.KMENotFoundError
