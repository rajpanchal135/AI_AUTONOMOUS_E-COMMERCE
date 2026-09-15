#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../lib/network-stack';
import { DataStack } from '../lib/data-stack';
import { ComputeStack } from '../lib/compute-stack';
import { EdgeStack } from '../lib/edge-stack';

const app = new cdk.App();
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT || process.env.AWS_ACCOUNT_ID,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};

const network = new NetworkStack(app, 'EcomAiNetworkStack', { env });
const data = new DataStack(app, 'EcomAiDataStack', { env, vpc: network.vpc });
const compute = new ComputeStack(app, 'EcomAiComputeStack', {
  env,
  vpc: network.vpc,
  database: data.database,
  redisEndpoint: data.redisEndpoint,
  knowledgeBucket: data.knowledgeBucket
});
const edge = new EdgeStack(app, 'EcomAiEdgeStack', {
  env,
  apiService: compute.apiService,
  webService: compute.webService
});

cdk.Tags.of(app).add('Project', 'EcomAutonomousPlatform');
cdk.Tags.of(app).add('ManagedBy', 'CDK');
