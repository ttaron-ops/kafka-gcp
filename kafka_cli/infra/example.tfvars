# app_project = {
#   name            = "c8r-dev",
#   id              = "c8r-dev",
# }

project_id = "c8r-test"
project_name = "c8r-test"
region = "us-west3"

vpc_peering_enabled = false

# vpc_peering = [
#   {
#     name         = "staging-to-ops"
#     peer_network = "projects/c8r-operations/global/networks/ops-vpc"
#   }
# ]


vpc = {
  vpc-name                = "kafka-vpc",
  default-subnet-creation = "false",
  subnet-name             = "vpc-subnet",
  proxy-subnet-name       = "proxy-only-subnet",
  proxy-subnet-cidr       = "10.101.0.0/16",
  main-cidr               = "10.1.0.0/16",
}

vpc_firewall = [
  {
    name          = "allow-ssh-v4"
    priority      = 1
    direction     = "INGRESS"
    source_ranges = ["54.70.239.162/32", "37.157.213.41/32", "87.241.132.135/32"]
    allow = [
      {
        protocol = "tcp"
        ports    = ["22"]
      }
    ]
  },
  {
    name          = "deny-ssh-v6"
    priority      = 11
    direction     = "INGRESS"
    source_ranges = ["::/0"]
    deny = [
      {
        protocol = "tcp"
        ports    = ["22"]
      }
    ]
  },
  {
    name          = "deny-ssh-v4"
    priority      = 11
    direction     = "INGRESS"
    source_ranges = ["0.0.0.0/0"]
    deny = [
      {
        protocol = "tcp"
        ports    = ["22"]
      }
    ]
  },
  {
    name          = "deny-rdp-v6"
    priority      = 11
    direction     = "INGRESS"
    source_ranges = ["::/0"]
    deny = [
      {
        protocol = "tcp"
        ports    = ["3389"]
      }
    ]
  },
  {
    name          = "deny-rdp-v4"
    priority      = 11
    direction     = "INGRESS"
    source_ranges = ["0.0.0.0/0"]
    deny = [
      {
        protocol = "tcp"
        ports    = ["3389"]
      }
    ]
  },
  {
    name          = "allow-proxy-connection"
    priority      = 123
    direction     = "INGRESS"
    source_ranges = ["10.120.0.0/23"]
    allow = [
      {
        protocol = "tcp"
        ports    = ["80", "8080", "443", "8443"]
      }
    ]
  },
  {
    name          = "deny-v6"
    priority      = 1111
    direction     = "INGRESS"
    source_ranges = ["::/0"]
    deny = [
      {
        protocol = "all"
      }
    ]
  },
  {
    name          = "deny-v4"
    priority      = 1111
    direction     = "INGRESS"
    source_ranges = ["0.0.0.0/0"]
    deny = [
      {
        protocol = "all"
      }
    ]
  },
  {
    name          = "vpc-internal"
    priority      = 10
    direction     = "INGRESS"
    source_ranges = ["10.1.0.0/16"]
    target_tags   = ["ops"]
    allow = [
      {
        protocol = "all"
      }
    ]
  }
]


















# keyring_enabled     = false
# gke_enabled         = false

# keyrings = [
#   {
#     ring_name = "c8r-staging"
#     keys = [
#       {
#         name                 = "c8r-general"
#         rotation_period      = "86400s"
#         purpose              = "ENCRYPT_DECRYPT"
#         key_algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
#         key_protection_level = "SOFTWARE"
#         labels               = {}
#       },
#       {
#         name                 = "c8r-storage"
#         rotation_period      = "86400s"
#         purpose              = "ENCRYPT_DECRYPT"
#         key_algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
#         key_protection_level = "SOFTWARE"
#         labels               = {}
#       },
#       {
#         name                 = "c8r-secrets"
#         rotation_period      = "86400s"
#         purpose              = "ENCRYPT_DECRYPT"
#         key_algorithm        = "GOOGLE_SYMMETRIC_ENCRYPTION"
#         key_protection_level = "SOFTWARE"
#         labels               = {}
#       }
#     ]
#   }
# ]
