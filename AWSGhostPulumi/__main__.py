"""An AWS Python Pulumi program"""

import pulumi
import pulumi_aws as aws

config = pulumi.Config()
data   = config.require_object("data")

#Create VPC
vpc = aws.ec2.Vpc(
   data.get("vpc_name"),
   cidr_block = data.get("vpc_cidr")
   )

#Create Internet Gateway
igw = aws.ec2.InternetGateway(
    data.get("igw_name"),
    vpc_id = vpc.id,
    tags = {
        "Name"  :   data.get("igw_name")
    })

#Create Private Subnet
PrivateSubnet = aws.ec2.Subnet(
    data.get("prv_subnet_name"),
    vpc_id = vpc.id,
    cidr_block = data.get("prv_cidr"),
    map_public_ip_on_launch = False,
    tags = {
        "Name"  :   data.get("prv_subnet_name"),
    })

#Create Public Subnet
PublicSubnet = aws.ec2.Subnet(
    data.get("pub_subnet_name"),
    vpc_id = vpc.id,
    cidr_block = data.get("pub_cidr"),
    map_public_ip_on_launch = True,
    tags = {
        "Name"  :   data.get("pub_subnet_name"),
    })

#Create Elastic IP

eip = aws.ec2.Eip(
    data.get("eip_name"),
    vpc = True
)

#Create NAT gateway
NatGateway = aws.ec2.NatGateway(
    data.get("nat_gw_name"),
    allocation_id = eip.allocation_id,
    subnet_id = PublicSubnet.id,

    tags = {
        "Name"  :   data.get("nat_gw_name")
    },
    opts = pulumi.ResourceOptions(depends_on=[igw])
    )

#Create public routing table
PubRouteTable = aws.ec2.RouteTable(
    data.get("pub_route_name"),
    vpc_id = vpc.id,
    routes = [
        aws.ec2.RouteTableRouteArgs(
            cidr_block = "0.0.0.0/0",
            gateway_id = igw.id,
        )
    ],
    tags = {
        "Name"  :   data.get("pub_route_name")
    })

#Create private routing table
PrvRouteTable = aws.ec2.RouteTable(
    data.get("prv_route_name"),
    vpc_id = vpc.id,
    routes = [
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id = NatGateway.id,
        )
    ],
    tags = {
        "Name"  :   data.get("prv_route_name"),
    })

#Public route assosication
pub_route_association = aws.ec2.RouteTableAssociation(
    data.get("pub_route_asso_name"),
    route_table_id = PubRouteTable.id,
    subnet_id = PublicSubnet.id
)

#Private route assosication
prv_route_association = aws.ec2.RouteTableAssociation(
    data.get("prv_route_asso_name"),
    route_table_id = PrvRouteTable.id,
    subnet_id = PrivateSubnet.id
)

sg_ec2 = aws.ec2.SecurityGroup(
    data.get("sec_ec2_gp_name"),
    description = "Allow HTTP/HTTPS trafic to EC2 instance",
    ingress=[{
        "protocol"  :   "tcp",
        "from_port" :   80,
        "to_port"   :   80,
        "cidr_blocks":  ["0.0.0.0/0"],
    },
    {
         "protocol"  :   "tcp",
        "from_port" :   443,
        "to_port"   :   443,
        "cidr_blocks":  ["0.0.0.0/0"],
    },
    {
        "protocol"  :   "tcp",
        "from_port" :   22,
        "to_port"   :   22,
        "cidr_blocks":  ["84.119.0.0/16"],
    },
    ],
    egress = [{
        "protocol"  :   "-1",
        "from_port" :   0,
        "to_port"   :   0,
        "cidr_blocks":  ["0.0.0.0/0"],
    }],
    vpc_id = vpc.id
)

ami = aws.ec2.get_ami(
    filters=[
        aws.ec2.GetAmiFilterArgs(
            name = "name",
            values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"],
        ),
        aws.ec2.GetAmiFilterArgs(
            name   = "virtualization-type",
            values = ["hvm"],
        ),
    ],
    most_recent = "true",
    owners=["099720109477"],
)

user_data = """
#!/bin/bash
echo "Hello, world!" > index.html
nohup python -m SimpleHTTPServer 80 &
"""

app_ec2_instance = aws.ec2.Instance(
        data.get("ec2_app_name"),
        instance_type = data.get("ec2_app_type"),
        vpc_security_group_ids = [sg_ec2.id],
        ami = ami.id,
        key_name = data.get("keypair_name"),
        subnet_id = PrivateSubnet.id,
)