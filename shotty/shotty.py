import boto3
import botocore
import click
def resource(profile):
    session = boto3.Session(profile_name= profile)
    ec2 = session.resource('ec2')
    return ec2

def filter_instances(project, ec2):
    instances = []
    
    if project:
        filters = [{'Name':'tag:Project', 'Values':[project]}]
        instances = ec2.instances.filter(Filters=filters)
    else:
        instances = ec2.instances.all()
    
    return instances

def has_pending_snapshot(volume):
    snapshot = list(volume.snapshot.all())
    return snapshots and snapshots[0].state == 'pending'

@click.group()
def cli():
    """ Shotty manages snapshots"""
@cli.group('snapshots')
def snapshots():
    """Commands for snapshots"""

@snapshots.command('list')
@click.option('--project', default=None, help="only snapshots for project (tag Project:<name>)")
@click.option('--all', 'list_all', default=False, is_flag=True, help="List all snapshots for each volume, not just most recent one")
@click.option('--profile', default= 'shotty', help="define profie name")
def list_snapshots(project, list_all, profile):
    "List EC2 snapshots"

    instances = filter_instances(project, resource(profile))
    for i in instances:
        for v in i.volumes.all():
            for s in v.snapshots.all():
                print(", ".join((
                    s.id,
                    v.id,
                    i.id,
                    s.state,
                    s.progress,
                    s.start_time.strftime("%c")
                    )))
                if s.state == 'completed' and not list_all: break
                
    return

@cli.group('volumes')
def volumes():
    """Commands for volumes"""

@volumes.command('list')
@click.option('--project', default=None, help="only volumes for project (tag Project:<name>)")
@click.option('--profile', default= 'shotty', help="define profie name")
def list_volumes(project, profile):
    "List EC2 volumes"

    instances = filter_instances(project, resource(profile))

    for i in instances:
        for v in i.volumes.all():
            print(", ".join((
                v.id,
                i.id,
                v.state,
                str(v.size) + "GiB",
                v.encrypted and "Encrypted" or "Not Encrypted"
                )))
    return

@cli.group('instances')
def instances():
    """Commands for instances"""

@instances.command('snapshot', help = "Create snapshots of volumes")
@click.option('--project', default=None, help="only instances for project (tag Project:<name>)")
@click.option('--force', 'f_command', default=False, is_flag=True, help="To force a command if no project flag is set")
@click.option('--profile', default= 'shotty', help="define profie name")
def create_snapshot(project, f_command, profile):
    if project != None or f_command:
        "Create snapshots for EC2 Instances"

        instances = filter_instances(project, resource(profile))
        for i in instances:
            print("Stopping {0} ...".format(i.id))

            i.stop()
            i.wait_until_stopped()

            for v in i.volumes.all():
                if has_pending_snapshot(v):
                    print("Skipping {0}, snapshot already in progress".format(v.id))
                    continue
                
                print("Creating snapshot of {0}".format(v.id))
                v.create_snapshot(Description="Created by SnapshotAlyzer 3000")
            
            print("Starting {0} ...".format(i.id))
            
            i.start()
            i.wait_until_running()

        print("Job's done!")

        return
    else:
        print(" There is no project flag or force flag for the command")

@instances.command('list')
@click.option('--project', default=None, help="only instances for project (tag Project:<name>)")
@click.option('--profile', default= 'shotty', help="define profie name")
def list_instances(project, profile):
    "List EC2 instances"

    instances = filter_instances(project, resource(profile))

    for i in instances:
        tags = { t['Key']: t['Value'] for t in i.tags or [] }
        print(', '.join((
            i.id,
            i.instance_type,
            i.placement['AvailabilityZone'],
            i.state['Name'],
            i.public_dns_name,
            tags.get('Project', '<no project>')
            )))
    return

@instances.command('stop')
@click.option('--project', default=None, help="only instances for project (tag Project:<name>)")
@click.option('--force', 'f_command', default=False, is_flag=True, help="To force a command if no project flag is set")
@click.option('--profile', default= 'shotty', help="define profie name")
def stop_instances(project, f_command, profile):
    if project != None or f_command:
        "Stop EC2 Instances"

        instances = filter_instances(project, resource(profile))
        
        for i in instances:
            print("Stopping {0} ...".format(i.id))
            try:
                i.stop()
            except botocore.exceptions.ClientError as e:
                print("Could not stop {0}. ".format(i.id) + str(e))
                continue

        return
    else:
        print(" There is no project flag or force flag for the command")

@instances.command('start')
@click.option('--project', default=None, help="only instances for project (tag Project:<name>)")
@click.option('--force', 'f_command', default=False, is_flag=True, help="To force a command if no project flag is set")
@click.option('--profile', default= 'shotty', help="define profie name")
def start_instances(project, f_command, profile):
    if project != None or f_command:
        "Start EC2 Instances"

        instances = filter_instances(project, resource(profile))
        
        for i in instances:
            print("Starting {0} ...".format(i.id))
            try:
                i.start()
            except botocore.exceptions.ClientError as e:
                print("Could not start {0}. ".format(i.id) + str(e))
                continue

        return
    else:
        print(" There is no project flag or force flag for the command")

@instances.command('reboot')
@click.option('--project', default=None, help="only instances for project (tag Project:<name>)")
@click.option('--force', 'f_command', default=False, is_flag=True, help="To force a command if no project flag is set")
@click.option('--profile', default= 'shotty', help="define profie name")
def reboot_instances(project, f_command, profile):
    if project != None or f_command:
        "Reboot EC2 Instances"

        instances = filter_instances(project, resource(profile))
        
        for i in instances:
            print("Rebooting {0} ...".format(i.id))
            if i.state['Name'] == 'running':
                try:
                    i.reboot()
                except botocore.exceptions.ClientError as e:
                    print("Could not Reboot {0}. ".format(i.id) + str(e))
                    continue
            else:
                print("Could not reboot because it in {0} stage".format(i.state['Name']))

        return
    else:
        print(" There is no project flag or force flag for the command")

if __name__ == '__main__':
    cli()