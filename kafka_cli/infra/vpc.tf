#################################
###       locals              ###
#################################

locals {
  processed_vpc_peering = var.vpc_peering_enabled ? [for peering in var.vpc_peering : {
    name         = peering.name
    network      = peering.network != null ? peering.network : google_compute_network.vpc[0].self_link
    peer_network = peering.peer_network
  }] : []
}

#################################
###       resources           ###
#################################

resource "google_compute_address" "public_ingress_ip" {
  count        = var.public_ingress_ip_count
  name         = "${var.public_ingress_ip_name}-${count.index + 1}"
  region       = var.region
  address_type = "EXTERNAL"
  project      = var.project_id
}


resource "google_compute_address" "private_ingress_ip" {
  count        = var.private_ingress_ip_count
  name         = "${var.private_ingress_ip_name}-${count.index + 1}"
  region       = var.region
  address_type = "INTERNAL"
  subnetwork   = google_compute_subnetwork.subnet.self_link
  project      = var.project_id
}

resource "google_compute_network" "vpc" {
  count                   = var.vpc_enabled ? 1 : 0
  project                 = var.project_id
  name                    = var.vpc.vpc_name
  auto_create_subnetworks = var.vpc.default_subnet_creation
}

resource "google_compute_subnetwork" "subnet" {
  count                     = var.vpc_enabled ? 1 : 0
  project                   = var.project_id
  name                      = var.vpc.subnet_name
  region                    = var.region
  network                   = google_compute_network.vpc[0].name
  ip_cidr_range             = var.vpc.main_cidr
  private_ip_google_access  = true

  depends_on = [google_compute_network.vpc]
}

resource "google_compute_subnetwork" "proxy_subnet" {
  count                     = var.vpc_enabled ? 1 : 0
  project                   = var.project_id
  name                      = var.vpc.proxy_subnet_name
  region                    = var.region
  network                   = google_compute_network.vpc[0].name
  ip_cidr_range             = var.vpc.proxy_subnet_cidr
  private_ip_google_access  = false
  purpose                   = "REGIONAL_MANAGED_PROXY"
  role                      = "ACTIVE"
  depends_on                = [google_compute_network.vpc]
}

resource "google_compute_address" "internal_with_subnet_and_address" {
  count = var.instance_count
  name         = "my-internal-address-${count.index}"
  subnetwork   = google_compute_subnetwork.subnet[0].id
  address_type = "INTERNAL"
  address      = "10.0.42.42"   #adjust
  region       = var.region
}

resource "google_compute_firewall" "firewall_vpc" {
  count = var.vpc_enabled ? length(var.vpc_firewall) : 0

  project                 = var.project_id
  network                 = google_compute_network.vpc[0].id
  name                    = var.vpc_firewall[count.index].name
  priority                = var.vpc_firewall[count.index].priority
  source_service_accounts = var.vpc_firewall[count.index].source_service_accounts
  source_ranges           = var.vpc_firewall[count.index].source_ranges
  source_tags             = var.vpc_firewall[count.index].source_tags
  target_tags             = var.vpc_firewall[count.index].target_tags
  direction               = var.vpc_firewall[count.index].direction

  dynamic "allow" {
    for_each = var.vpc_firewall[count.index].allow
    content {
      protocol = allow.value.protocol
      ports    = allow.value.ports
    }
  }

  dynamic "deny" {
    for_each = var.vpc_firewall[count.index].deny
    content {
      protocol = deny.value.protocol
      ports    = deny.value.ports
    }
  }

  depends_on = [google_compute_network.vpc]
}

resource "google_compute_network_peering" "peering_connection" {
  count = var.vpc_peering_enabled ? length(local.processed_vpc_peering) : 0

  name                                = local.processed_vpc_peering[count.index].name
  network                             = local.processed_vpc_peering[count.index].network
  peer_network                        = local.processed_vpc_peering[count.index].peer_network
  export_subnet_routes_with_public_ip = false
  import_subnet_routes_with_public_ip = false
  depends_on                          = [google_compute_network.vpc]
  export_custom_routes                = true
  import_custom_routes                = true
}