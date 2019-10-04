"""
Basic machine settings for epsman scripts.
02/10/19
"""

# Currently just set for local run in iPython env.
# Should Functionalise, and set proper machine look-up.

from fabric import Connection
import getpass

if machine == 'AntonJr':
    # Set working environment
    wrkdir='/home/paul/ePS_stuff'
    scpdir = wrkdir + '/scripts2019'

    # Settings from ePS_batch_job.sh
    ePSpath='/opt/ePolyScat.E3/bin/ePolyScat'
    jobPath='/home/paul/ePS_stuff/jobs'

    # Log in to machine
    user='paul'

    if remoteFlag == True:
        # Remote connection settings
        host='10.8.0.6'

    else:
        # Set local credentials, then pass to Fabric.
        # This allows commands to run on local or remote host later, without any additional code required.
        host = 'localhost'
         # For local machine, 'user=!whoami'  # Works directly in Jupyter/iPython, but not in script

    print('Connecting to machine: ', host)

    # remotePass = input("Password for remote machine? ")
    remotePass = getpass.getpass("Password for machine? ")

    print('Testing connection...')

    # Connect to remote
    # With password passed explicitly (should also pick up keys from default location ~/.ssh/)
    c = Connection(
        host=host,
        user=user,
        connect_kwargs={
            "password": remotePass,
        },
    )

    test = c.run('hostname')
    # c.is_connected    # Another basic check.

    if test.return_code == 0:
        print('Connected OK')
        print(test)
    else:
        print('Connection failed')
        print(test)
