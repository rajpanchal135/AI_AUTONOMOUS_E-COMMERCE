import * as cdk from 'aws-cdk-lib';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { Construct } from 'constructs';

export interface EdgeStackProps extends cdk.StackProps {
  apiService: ecs.FargateService;
  webService: ecs.FargateService;
}

export class EdgeStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;

  constructor(scope: Construct, id: string, props: EdgeStackProps) {
    super(scope, id, props);

    // Cognito User Pool for Authentication
    this.userPool = new cognito.UserPool(this, 'EcomUserPool', {
      userPoolName: 'ecom-ai-operators',
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      autoVerify: { email: true },
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
    });

    const client = this.userPool.addClient('WebClient', {
      userPoolClientName: 'ecom-web-client',
      authFlows: { userPassword: true, userSrp: true },
    });

    // Public Application Load Balancer
    const alb = new elbv2.ApplicationLoadBalancer(this, 'PublicAlb', {
      vpc: props.apiService.cluster.vpc,
      internetFacing: true,
    });

    const httpListener = alb.addListener('HttpListener', {
      port: 80,
      open: true,
    });

    // Route /api/* to FastAPI, everything else to Web
    const apiTargetGroup = httpListener.addTargets('ApiTarget', {
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [props.apiService],
      healthCheck: { path: '/api/v1/health/live' },
      priority: 10,
      conditions: [elbv2.ListenerCondition.pathPatterns(['/api/*', '/docs*'])],
    });

    httpListener.addTargets('WebTarget', {
      port: 3000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [props.webService],
      healthCheck: { path: '/' },
    });

    new cdk.CfnOutput(this, 'AlbEndpoint', {
      value: alb.loadBalancerDnsName,
      description: 'Public Application Load Balancer DNS Name',
    });
  }
}
