import boto3
import botocore
import click
import datetime

class Info(object):

    def __init__(self):
        self.profile = False

pass_info = click.make_pass_decorator(Info, ensure=True)

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
    snapshots = list(volume.snapshots.all())
    return snapshots and snapshots[0].state == 'pending'

@click.group()
@click.option('--profile', default= 'shotty', help="define profie name")
@pass_info
def cli(info, profile):
    """ Shotty manages snapshots"""
    info.profile= profile

@cli.group('snapshots')
def snapshots():
    """Commands for snapshots"""

@snapshots.command('list')
@pass_info
@click.option('--project', default=None, help="only snapshots for project (tag Project:<name>)")
@click.option('--all', 'list_all', default=False, is_flag=True, help="List all snapshots for each volume, not just most recent one")
@click.option('--instance', default=None, help="only for specified instance id")
def list_snapshots(info, project, list_all, instance):
    if not instance:
        "List EC2 snapshots"

        instances = filter_instances(project, resource(info.profile))
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
    else:
        inst = resource(info.profile).Instance(instance)
        for v in inst.volumes.all():
            for s in v.snapshots.all():
                print(", ".join((
                    s.id,
                    v.id,
                    inst.id,
                    s.state,
                    s.progress,
                    s.start_time.strftime("%c")
                    )))
                if s.state == 'completed' and not list_all: break

@cli.group('volumes')
def volumes():
    """Commands for volumes"""

@volumes.command('list')
@pass_info
@click.option('--project', default=None, help="only volumes for project (tag Project:<name>)")
@click.option('--instance', default=None, help="only for specified instance id")
def list_volumes(info, project, instance):
    if not instance:
        "List EC2 volumes"

        instances = filter_instances(project, resource(info.profile))

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
    else:
        inst = resource(info.profile).Instance(instance)
        for v in inst.volumes.all():
            print(", ".join((
                v.id,
                inst.id,
                v.state,
                str(v.size) + "GiB",
                v.encrypted and "Encrypted" or "Not Encrypted"
                )))

@cli.group('instances')
def instances():
    """Commands for instances"""

@instances.command('snapshot', help = "Create snapshots of volumes")
@pass_info
@click.option('--project', default=None, help="only instances for project (tag Project:<name>)")
@click.option('--force', 'f_command', default=False, is_flag=True, help="To force a command if no project flag is set")
@click.option('--instance', default=None, help="only for specified instance id")
@click.option('--age', default=None, required= True, type= int, help="age in days to create new snapshot")
def create_snapshot(info, project, f_command, instance, age):
    if not instance:
        if project != None or f_command:
            "Create snapshots for EC2 Instances"

            instances = filter_instances(project, resource(info.profile))
            for i in instances:
                if i.state['Name'] == 'running':
                    for v in i.volumes.all():
                        if has_pending_snapshot(v):
                            print("Skipping {0}, snapshot already in progress".format(v.id))
                            continue
                        k = [ s for s in v.snapshots.all()]
                        if not k == []:
                            for s in v.snapshots.all():
                                tz_info = s.start_time.tzinfo
                                diff = datetime.datetime.now(tz_info)-s.start_time
                                if diff.days >= age:
                                    try:
                                        print("Stopping {0} ...".format(i.id))
                                        i.stop()
                                        i.wait_until_stopped()
                                        print("Creating snapshot of {0}".format(v.id))
                                        v.create_snapshot(Description="Created by SnapshotAlyzer 3000")
                                        print("Starting {0} ...".format(i.id))
                                        i.start()
                                        i.wait_until_running()
                                    except botocore.exceptions.ClientError as e:
                                        print("Could not stop {0}. ".format(i.id) + str(e))
                                        continue
                                else:
                                    print("Snapshot is not older than given days")
                                if s.state == 'completed':break
                        else:
                            try:
                                print("Stopping {0} ...".format(i.id))
                                i.stop()
                                i.wait_until_stopped()
                                print("Creating snapshot of {0}".format(v.id))
                                v.create_snapshot(Description="Created by SnapshotAlyzer 3000")
                                print("Starting {0} ...".format(i.id))
                                i.start()
                                i.wait_until_running()
                            except botocore.exceptions.ClientError as e:
                                print("Could not stop {0}. ".format(i.id) + str(e))
                                continue
                else:
                    try:
                        for v in i.volumes.all():
                            if has_pending_snapshot(v):
                                print("Skipping {0}, snapshot already in progress".format(v.id))
                                continue
                            for s in v.snapshots.all():
                                tz_info = s.start_time.tzinfo
                                diff = datetime.datetime.now(tz_info)-s.start_time
                                if diff.days >= age:
                                    print("Creating snapshot of {0}".format(v.id))
                                    v.create_snapshot(Description="Created by SnapshotAlyzer 3000")
                                else:
                                    print("Snapshot is not older than given days")
                                if s.state == 'completed':break
                            
                    except botocore.exceptions.ClientError as e:
                        print("Could not stop {0}. ".format(i.id) + str(e))
                        continue

            print("Job's done!")

            return
        else:
            print(" There is no project flag or force flag for the command")
    else:
        inst = resource(info.profile).Instance(instance)
        if inst.state['Name'] == 'running':
            for v in inst.volumes.all():
                if has_pending_snapshot(v):
                    print("Skipping {0}, snapshot already in progress".format(v.id))
                    continue
                k = [ s for s in v.snapshots.all()]
                if not k == []:
                    for s in v.snapshots.all():
                        tz_info = s.start_time.tzinfo
                        diff = datetime.datetime.now(tz_info)-s.start_time
                        if diff.days >= age:
                            try:
                                print("Stopping {0} ...".format(inst.id))
                                inst.stop()
                                inst.wait_until_stopped()
                                print("Creating snapshot of {0}".format(v.id))
                                v.create_snapshot(Description="Created by SnapshotAlyzer 3000")
                                print("Starting {0} ...".format(inst.id))
                                inst.start()
                                inst.wait_until_running()
                            except botocore.exceptions.ClientError as e:
                                print("Could not stop {0}. ".format(inst.id) + str(e))
                        else:
                            print("Snapshot is not older than given days")
                        if s.state == 'completed':break
                else:
                    try:
                        print("Stopping {0} ...".format(inst.id))
                        inst.stop()
                        inst.wait_until_stopped()
                        print("Creating snapshot of {0}".format(v.id))
                        v.create_snapshot(Description="Created by SnapshotAlyzer 3000")
                        print("Starting {0} ...".format(inst.id))
                        inst.start()
                        inst.wait_until_running()
                    except botocore.exceptions.ClientError as e:
                        print("Could not stop {0}. ".format(inst.id) + str(e))
        else:
            try:
                for v in inst.volumes.all():
                    if has_pending_snapshot(v):
                        print("Skipping {0}, snapshot already in progress".format(v.id))
                        continue
                    for s in v.snapshots.all():
                        tz_info = s.start_time.tzinfo
                        diff = datetime.datetime.now(tz_info)-s.start_time
                        if diff.days >= age:
                            print("Creating snapshot of {0}".format(v.id))
                            v.create_snapshot(Description="Created by SnapshotAlyzer 3000")
                        else:
                            print("Snapshot is not older than given days")
                        if s.state == 'completed':break

            except botocore.exceptions.ClientError as e:
                print("Could not stop {0}. ".format(inst.id) + str(e))
        print("Job's done!")

@instances.command('list')
@pass_info
@click.option('--project', default=None, help="only instances for project (tag Project:<name>)")
def list_instances(info, project):
    "List EC2 instances"

    instances = filter_instances(project, resource(info.profile))

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
@pass_info
@click.option('--project', default=None, help="only instances for project (tag Project:<name>)")
@click.option('--force', 'f_command', default=False, is_flag=True, help="To force a command if no project flag is set")
@click.option('--instance', default=None, help="only for specified instance id")
def stop_instances(info, project, f_command, instance):
    if not instance:
        if project != None or f_command:
            "Stop EC2 Instances"

            instances = filter_instances(project, resource(info.profile))
            
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
    else:
        inst = resource(info.profile).Instance(instance)
        print("Stopping {0} ...".format(inst.id))
        try:
            inst.stop()
        except botocore.exceptions.ClientError as e:
            print("Colud not Stop {0}. ".format(inst.id) + str(e))

@instances.command('start')
@pass_info
@click.option('--project', default=None, help="only instances for project (tag Project:<name>)")
@click.option('--force', 'f_command', default=False, is_flag=True, help="To force a command if no project flag is set")
@click.option('--instance', default=None, help="only for specified instance id")
def start_instances(info, project, f_command, instance):
    if not instance:
        if project != None or f_command:
            "Start EC2 Instances"

            instances = filter_instances(project, resource(info.profile))
            
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
    else:
        inst = resource(info.profile).Instance(instance)
        print("Starting {0} ...".format(inst.id))
        try:
            inst.start()
        except botocore.exceptions.ClientError as e:
            print("Colud not start {0}. ".format(inst.id) + str(e))
        

@instances.command('reboot')
@pass_info
@click.option('--project', default=None, help="only instances for project (tag Project:<name>)")
@click.option('--force', 'f_command', default=False, is_flag=True, help="To force a command if no project flag is set")
@click.option('--instance', default=None, help="only for specified instance id")
def reboot_instances(info, project, f_command, instance):
    if not instance:
        if project != None or f_command:
            "Reboot EC2 Instances"

            instances = filter_instances(project, resource(info.profile))
            
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
    else:
        inst = resource(info.profile).Instance(instance)
        print("Rebooting {0} ...".format(inst.id))
        if inst.state['Name'] == 'running':
            try:
                inst.reboot()
            except botocore.exceptions.ClientError as e:
                print("Colud not Reboot {0}. ".format(inst.id) + str(e))
        else:
            print("Could not reboot because it in {0} stage".format(inst.state['Name']))

if __name__ == '__main__':
    cli()