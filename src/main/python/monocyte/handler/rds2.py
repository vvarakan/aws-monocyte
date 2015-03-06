# Monocyte - Search and Destroy unwanted AWS Resources relentlessly.
# Copyright 2015 Immobilien Scout GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import boto
import boto.rds2
from monocyte.handler import Resource, Handler

SKIPPING_CREATION_STATEMENT = "\tCurrently in creation. Skipping."
SKIPPING_AUTOGENERATED_STATEMENT = "\tNot a manually created Snapshot. Skipping."
SKIPPING_DELETION_STATEMENT = "\tDeletion already in progress. Skipping."
DELETION_STATEMENT = "\tInitiating deletion sequence."
DRY_RUN_STATEMENT = "\tDRY RUN: Would be deleted otherwise."

CREATION_STATUS = "creating"
AUTOMATED_STATUS = "automated"
DELETION_STATUS = "deleting"


class Instance(Handler):

    def fetch_regions(self):
        return boto.rds2.regions()

    def fetch_unwanted_resources(self):
        for region in self.regions:
            connection = boto.rds2.connect_to_region(region.name)
            resources = connection.describe_db_instances() or []
            for resource in resources["DescribeDBInstancesResponse"]["DescribeDBInstancesResult"]["DBInstances"]:
                yield Resource(resource, region.name)

    def to_string(self, resource):
        return "Database Instance found in {region} \n\t".format(**vars(resource)) + \
               "{DBInstanceIdentifier}, status {DBInstanceStatus}".format(**resource.wrapped)

    def delete(self, resource):
        if self.dry_run:
            self.logger.info(DRY_RUN_STATEMENT)
            return
        if resource.wrapped["DBInstanceStatus"] == DELETION_STATUS:
            self.logger.info(SKIPPING_DELETION_STATEMENT)
            return
        self.logger.info(DELETION_STATEMENT)
        connection = boto.rds2.connect_to_region(resource.region)
        response = connection.delete_db_instance(resource.wrapped["DBInstanceIdentifier"], skip_final_snapshot=True)
        return response["DeleteDBInstanceResponse"]["DeleteDBInstanceResult"]["DBInstance"]


class Snapshot(Handler):

    def fetch_regions(self):
        return boto.rds2.regions()

    def fetch_unwanted_resources(self):
        for region in self.regions:
            connection = boto.rds2.connect_to_region(region.name)
            resources = connection.describe_db_snapshots() or []
            for resource in resources["DescribeDBSnapshotsResponse"]["DescribeDBSnapshotsResult"]["DBSnapshots"]:
                yield Resource(resource, region.name)

    def to_string(self, resource):
        return "Database Snapshot found in {region} \n\t".format(**vars(resource)) + \
               "{DBSnapshotIdentifier}, status {Status}".format(**resource.wrapped)

    def delete(self, resource):
        if self.dry_run:
            self.logger.info(DRY_RUN_STATEMENT)
            return
        if resource.wrapped["Status"] == DELETION_STATUS:
            self.logger.info(SKIPPING_DELETION_STATEMENT)
            return
        if resource.wrapped["Status"] == CREATION_STATUS:
            self.logger.info(SKIPPING_CREATION_STATEMENT)
            return
        if resource.wrapped["SnapshotType"] == AUTOMATED_STATUS:
            self.logger.info(SKIPPING_AUTOGENERATED_STATEMENT)
            return
        self.logger.info(DELETION_STATEMENT)
        connection = boto.rds2.connect_to_region(resource.region)
        response = connection.delete_db_snapshot(resource.wrapped["DBSnapshotIdentifier"])
        return response["DeleteDBSnapshotResponse"]["DeleteDBSnapshotResult"]["DBSnapshot"]
