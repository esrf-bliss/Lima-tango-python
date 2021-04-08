Memcached
=========

This plugins aims to publish the frames to a [memcached storage](https://memcached.org/about), a high performance multithreaded event-based key/value cache store intended to be used in a distributed system.

Once configured you can start the task using **Start** command and stop the task calling the **Stop** command.

Properties
----------
======================= =============== =============== ================================================
Property name           Mandatory       Default value   Description
======================= =============== =============== ================================================
ServerIP                Yes             127.0.0.1       The server IP
ServerPort              Yes             11211           The server Port
Default AcquisitionID   Yes             default         The default acquisition ID set a startup
======================= =============== =============== ================================================

Attributes
----------
======================= ======= ======================= ===================================================
Attribute name          RW      Type                    Description
======================= ======= ======================= ===================================================
AcquisitionID           RW      DevString               Unique identifier of the acquisition (basename for the key)
Stats                   RO      DevString               Memcached server statistics encoded as JSON
RunLevel                RW      DevLong                 Run level in the processing chain, from 0 to N        
State                   RO      State                   OFF or ON (stopped or started)
Status                  RO      DevString               "OFF" "ON" (stopped or started)
======================= ======= ======================= ===================================================


Commands
--------
======================= ================== ======================= =======================================
Command name            Arg. in            Arg. out                Description
======================= ================== ======================= =======================================
Init                    DevVoid            DevVoid                 Do not use
Start                   DevVoid            DevVoid                 Start the operation on image
State                   DevVoid            DevLong                 Return the device state
Status                  DevVoid            DevString               Return the device state as a string
Stop                    DevVoid            DevVoid                 Stop the operation on image
FlushAll                DevVoid            DevVoid                 Invalidate all existing cache items
======================= ================== ======================= =======================================
