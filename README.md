# snaphotalyzer-30000

Demo project to manage EC2 instance snapshots

## About

This project is a demo, and uses boto3 to manage AWS EC2 instances snapshots.

## Configuring

shotty uses the configuration file created by the AWS cli. e.g.

`aws configure --profile shotty`

## Running 

`pipenv run "python shotty/shotty.py <--profile=Name> <--region=Name> <command> <subcommand> <--project=PROJECT>" <--force> <--instance> <--all> <--age>`

*profile* is for using different aws profiles
*region* is for using fifferent region than the specified region in profiles
*command* is instances,volumes, or snapshots
*subcommand* - depends on command  
*project* is optional
*force* is to force anything without project flag
*instance* is for specific instance id
*all* is used for listing all snapshots
*age* is used for creating snapshot which are older than given age in days