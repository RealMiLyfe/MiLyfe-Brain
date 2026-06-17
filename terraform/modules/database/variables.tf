variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "db_instance_class" {
  type = string
}

variable "allocated_storage" {
  type = number
}

variable "redis_node_type" {
  type = string
}

variable "allowed_security_groups" {
  type = list(string)
}
