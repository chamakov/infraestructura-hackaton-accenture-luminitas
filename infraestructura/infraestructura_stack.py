from aws_cdk import (
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_dynamodb as ddb,
    aws_s3_notifications as s3_notifications,
    aws_cognito as cog,
    aws_apigateway as apiw,
    aws_opensearchservice as osh,
    core as cdk
)


class InfraestructuraStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        stage = 'dev'

        #Grupos para cognito
        groupWAUsr = iam.Group(self, "Lumi-WebAppUsrGroup-" + stage)
        groupWAAdm = iam.Group(self, "Lumi-WebAppAdminGroup-" + stage)y

        permissionsBoundary = iam.ManagedPolicy.from_managed_policy_name(
            self, 'ScopePermissions', 'ScopePermissions'
        )

        lambdaRole = iam.Role(self, assumed_by= iam.ServicePrincipal('lambda.amazonaws.com'),
                              permissions_boundary=permissionsBoundary, role_name='RoleLambdaLuminitas',
                              id='RoleLambdaLumis')
        lambdaRole.add_managed_policy(
            #iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name='AWSLambdaBasicExecutionRole'))
            iam.ManagedPolicy.from_managed_policy_arn(self,id='BasicAccess', managed_policy_arn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'))

        s3Role = iam.Role(self, assumed_by=iam.ServicePrincipal('s3.amazonaws.com'),
                              permissions_boundary=permissionsBoundary, role_name='RoleS3Luminitas',
                              id='RoleS3Lumis')
        s3Role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name='AmazonS3FullAccess'))

        # S3 para las imagenes
        bucket = s3.Bucket(self, 'BucketImgLumi-' + stage,
                           removal_policy=cdk.RemovalPolicy.DESTROY) #Esto no se usa en produccion

        #Permisos para los grupos para cognito
        bucket.grant_read_write(groupWAUsr)
        bucket.grant_read_write(groupWAAdm)

        #DynamoDB para guardar los resultados de rekognition
        table = ddb.Table(
            self, 'Classifications',
            partition_key={'name': 'image_name', 'type': ddb.AttributeType.STRING}
        )

        capConfig = osh.CapacityConfig(data_node_instance_type='T3.small.search', data_nodes=1)

        devDomain = osh.Domain(self, 'LuminitasDomain',
                               version=osh.EngineVersion.ELASTICSEARCH_7_1,
                               capacity=capConfig,
                               encryption_at_rest={
                                   "enabled": True
                               }
                               )

        # Lambda para trigger de carga de fotografias
        lambda_function = _lambda.Function(
            self, 'LambdaRek-' + stage,
            runtime = _lambda.Runtime.PYTHON_3_8,
            handler = 'lambda-handler.main',
            code = _lambda.Code.asset('./lambda/cargaFotografias'),
            environment = {
                'BUCKET_NAME': bucket.bucket_name,
                'TABLE_NAME': table.table_name,
                'ELASTIC_SEARCH': devDomain.domain_endpoint
            },
            role= lambdaRole
        )

        # permisos para RW para la lambda
        bucket.grant_read_write(lambda_function)

        # Lambda para obtener un listado de fotografias
        lambda_obtener_todo = _lambda.Function(
            self, 'LambdaGetFotos-' + stage,
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='lambda-handler.main',
            code= _lambda.Code.asset('./lambda/getFotografias'),
            environment={
                'ELASTIC_SEARCH' : devDomain.domain_endpoint
            },
            role= lambdaRole
        )

        # Lambda para borrar una fotografia
        lambda_borrar_foto = _lambda.Function(
            self, 'LambdaBorrarFotos-' + stage,
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='lambda-handler.main',
            code=_lambda.Code.asset('./lambda/borraFotografia'),
            environment={
                'ELASTIC_SEARCH': devDomain.domain_endpoint
            },
            role= lambdaRole
        )

        # Lambda para buscar fotografia
        lambda_buscar_foto = _lambda.Function(
            self, 'LambdaBuscarFotos-' + stage,
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='lambda-handler.main',
            code=_lambda.Code.asset('./lambda/buscaFotografias'),
            environment={
                'ELASTIC_SEARCH': devDomain.domain_endpoint
            },
            role= lambdaRole
        )

        # Lambda para cargar fotografia
        lambda_subir_foto = _lambda.Function(
            self, 'LambdaSubirFotos-' + stage,
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='lambda-handler.main',
            code=_lambda.Code.asset('./lambda/subirFotografia'),
            environment={
                'BUCKET_NAME': bucket.bucket_name
            },
            role= lambdaRole
        )

        #Permisos para subir fotos
        bucket.grant_read_write(lambda_subir_foto)

        # Permisos para rekognition en la lambda
        statement = iam.PolicyStatement()
        statement.add_actions("rekognition:DetectLabels")
        statement.add_resources("*")
        lambda_function.add_to_role_policy(statement)

        # Desencadenante para S3 para llamar la lambda, considerando sufijos especificos
        notification = s3_notifications.LambdaDestination(lambda_function)
        notification.bind(self, bucket)
        bucket.add_object_created_notification(notification, s3.NotificationKeyFilter(suffix='.jpg'))
        bucket.add_object_created_notification(notification, s3.NotificationKeyFilter(suffix='.jpeg'))
        bucket.add_object_created_notification(notification, s3.NotificationKeyFilter(suffix='.png'))

        bucket.grant_read_write(lambda_function)

        # permisos para dynamodb
        table.grant_read_write_data(lambda_function)

        # Api Gateway
        #corsOptions = apiw.CorsOptions(allow_origins=['*'])
        api_gateway = apiw.RestApi(self, 'Lumi-api-rekog-' + stage, rest_api_name='ApiBusquedaFotografias', cloud_watch_role=False)
        apw_resource = api_gateway.root.add_resource('LumiRekogApi')
        apw_fotografias_resource = apw_resource.add_resource('fotografias',
                                                             default_cors_preflight_options=apiw.CorsOptions(
                                                                 allow_methods=['GET', 'PUT', 'DELETE', 'POST' 'OPTIONS'],
                                                                 allow_origins=apiw.Cors.ALL_ORIGINS)
                                                             )

        get_fotografias_integration = apiw.LambdaIntegration(
            lambda_obtener_todo,
            proxy=True
        )

        borrar_fotografias_integration = apiw.LambdaIntegration(
            lambda_borrar_foto,
            proxy=True
        )

        buscar_fotografias_integration = apiw.LambdaIntegration(
            lambda_buscar_foto,
            proxy=True
        )

        subir_fotografias_integration = apiw.LambdaIntegration(
            lambda_subir_foto,
            proxy=True
        )

        getFotoMethod = apw_fotografias_resource.add_method(
            'GET', get_fotografias_integration,
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }]
        )

        borrarFotoMethod = apw_fotografias_resource.add_method(
            'DELETE', borrar_fotografias_integration,
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }]
        )

        buscarFotoMethod = apw_fotografias_resource.add_method(
            'POST', buscar_fotografias_integration,
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }]
        )

        subirFotoMethod = apw_fotografias_resource.add_method(
            'PUT', subir_fotografias_integration,
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }]
        )

        #Cognito

        required_attribute = cog.StandardAttribute(required=True)

        users_pool = cog.UserPool(
            self, 'Luminitas-usr-pool',
            auto_verify= cog.AutoVerifiedAttrs(email=True),
            standard_attributes=cog.StandardAttributes(email=required_attribute),
            self_sign_up_enabled=True
        )

        user_pool_app_client = cog.CfnUserPoolClient(
            self, 'Luminitas-usr-pool-app-client',
            supported_identity_providers=['COGNITO'],
            user_pool_id=users_pool.user_pool_id,
            explicit_auth_flows=['ALLOW_REFRESH_TOKEN_AUTH','ALLOW_USER_PASSWORD_AUTH','ALLOW_USER_SRP_AUTH']
        )

        cognito_groups = cog.CfnUserPoolGroup(
            self, 'Luminitas-Admin-Group',
            user_pool_id= users_pool.user_pool_id,
            description='Grupo de administradores',
            group_name='Admin-Group',
            precedence=1
        )

        cognito_groups = cog.CfnUserPoolGroup(
            self, 'Luminitas-User-Group',
            user_pool_id=users_pool.user_pool_id,
            description='Grupo de usuarios',
            group_name='Usr-Group',
            precedence=1
        )

        apw_auth = apiw.CfnAuthorizer(
            self, 'Luminitas-authorizer',
            rest_api_id=apw_resource.rest_api.rest_api_id,
            name='AUTHORIZER-LUMINITAS-PROJ',
            type='COGNITO_USER_POOLS',
            identity_source="method.request.header.Authorization",
            provider_arns=[users_pool.user_pool_arn]
        )

        #Aseguramos los endpoints
        gFoto = getFotoMethod.node.find_child('Resource')
        gFoto.add_property_override('AuthorizationType', 'COGNITO_USER_POOLS')
        gFoto.add_property_override('AuthorizerId', { "Ref": apw_auth.logical_id})

        bFoto = borrarFotoMethod.node.find_child('Resource')
        bFoto.add_property_override('AuthorizationType', 'COGNITO_USER_POOLS')
        bFoto.add_property_override('AuthorizerId', {"Ref": apw_auth.logical_id})

        buFoto = buscarFotoMethod.node.find_child('Resource')
        buFoto.add_property_override('AuthorizationType', 'COGNITO_USER_POOLS')
        buFoto.add_property_override('AuthorizerId', {"Ref": apw_auth.logical_id})

        sFoto = subirFotoMethod.node.find_child('Resource')
        sFoto.add_property_override('AuthorizationType', 'COGNITO_USER_POOLS')
        sFoto.add_property_override('AuthorizerId', {"Ref": apw_auth.logical_id})

        devDomain.grant_read_write(lambda_borrar_foto)
        devDomain.grant_read_write(lambda_buscar_foto)
        devDomain.grant_read_write(lambda_obtener_todo)
        devDomain.grant_read_write(lambda_function)

