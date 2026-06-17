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

variable "cluster_version" {
  type = string
}

variable "node_instance_types" {
  type = list(string)
}

variable "min_nodes" {
  type = number
}

variable "max_nodes" {
  type = number
}

variable "desired_nodes" {
  type = number
}

variable "enable_gpu_nodes" {
  type    = bool
  default = false
}

variable "gpu_instance_types" {
  type    = list(string)
  default = ["g4dn.xlarge"]
}
