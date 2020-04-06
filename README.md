# snaphotalyzer-30000

Demo project to manage EC2 instance snapshots

## About

This project is a demo, and uses boto3 to manage AWS EC2 instances snapshots.

## Configuring

shotty uses the configuration file created by the AWS cli. e.g.

`aws configure --profile shotty`

## Running 

`pipenv run "python shotty/shotty.py <--profile=Name> <command> <subcommand> <--project=PROJECT>" <--force>`

*profile* is for using different aws profiles
*command* is instances,volumes, or snapshots
*subcommand* - depends on command  
*project* is optional
*force* is to force anything without project flag