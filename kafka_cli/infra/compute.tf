resource "aws_instance" "kafka" {
  count         = var.kafka_instance_count
  ami           = var.kafka_ami_id
  instance_type = var.kafka_instance_type

  tags = merge(
    var.kafka_tags,
    {
      Name = "kafka-instance-${count.index}"
    }
  )

  network_interface {
    device_index         = 0
    subnet_id            = var.kafka_subnet_id
    associate_public_ip_address = var.kafka_associate_public_ip
    security_groups      = var.kafka_security_groups
  }

  root_block_device {
    volume_size = var.kafka_root_volume_size
    volume_type = var.kafka_root_volume_type
  }

  user_data = var.kafka_user_data
}
