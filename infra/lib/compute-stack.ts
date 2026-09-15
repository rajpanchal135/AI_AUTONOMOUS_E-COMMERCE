import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as events from 'aws-cdk-lib/aws-events';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as rds from 'aws-cdk-lib/aws-rds';
import { Construct } from 'constructs';

export interface ComputeStackProps extends cdk.StackProps {
  vpc: ec2.IVpc;
  database: rds.DatabaseCluster;
  redisEndpoint: string;
  knowledgeBucket: s3.IBucket;
}

export class ComputeStack extends cdk.Stack {
  public readonly apiService: ecs.FargateService;
  public readonly webService: ecs.FargateService;
  public readonly agentQueue: sqs.Queue;
  public readonly eventBus: events.EventBus;

  constructor(scope: Construct, id: string, props: ComputeStackProps) {
    super(scope, id, props);

    const cluster = new ecs.Cluster(this, 'EcomAiCluster', {
      vpc: props.vpc,
      containerInsights: true,
    });

    // SQS Dead Letter Queue & Agent Queue
    const dlq = new sqs.Queue(this, 'AgentDeadLetterQueue', {
      retentionPeriod: cdk.Duration.days(14),
    });

    this.agentQueue = new sqs.Queue(this, 'AgentTasksQueue', {
      visibilityTimeout: cdk.Duration.seconds(300),
      deadLetterQueue: { maxReceiveCount: 3, queue: dlq },
    });

    this.eventBus = new events.EventBus(this, 'CommerceEventBus', {
      eventBusName: 'ecom-commerce-events',
    });

    // IAM Role with Bedrock least-privilege permissions
    const taskRole = new iam.Role(this, 'EcsAgentTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });
    taskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
        resources: ['*'],
      })
    );
    props.knowledgeBucket.grantReadWrite(taskRole);
    this.agentQueue.grantConsumeMessages(taskRole);

    // API Fargate Service
    const apiTaskDef = new ecs.FargateTaskDefinition(this, 'ApiTaskDef', {
      memoryLimitMiB: 2048,
      cpu: 1024,
      taskRole,
    });
    const apiContainer = apiTaskDef.addContainer('ApiContainer', {
      image: ecs.ContainerImage.fromAsset('.', {
        file: 'docker/api.Dockerfile',
      }),
      logging: ecs.LogDrivers.awsLogs({ streamPrefix: 'ecom-api' }),
      environment: {
        APP_ENV: 'production',
        AWS_REGION: this.region,
        DEFAULT_AUTONOMY_LEVEL: '2',
      },
    });
    apiContainer.addPortMappings({ containerPort: 8000 });

    this.apiService = new ecs.FargateService(this, 'ApiService', {
      cluster,
      taskDefinition: apiTaskDef,
      desiredCount: 2,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
    });

    // Web Fargate Service
    const webTaskDef = new ecs.FargateTaskDefinition(this, 'WebTaskDef', {
      memoryLimitMiB: 1024,
      cpu: 512,
    });
    const webContainer = webTaskDef.addContainer('WebContainer', {
      image: ecs.ContainerImage.fromAsset('apps/web', {
        file: 'Dockerfile',
      }),
      logging: ecs.LogDrivers.awsLogs({ streamPrefix: 'ecom-web' }),
    });
    webContainer.addPortMappings({ containerPort: 3000 });

    this.webService = new ecs.FargateService(this, 'WebService', {
      cluster,
      taskDefinition: webTaskDef,
      desiredCount: 2,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
    });
  }
}
