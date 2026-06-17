variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

variable "availability_zones" {
  type = list(string)
}

variable "enable_waf" {
  type    = bool
  default = true
}

variable "domain_name" {
  type    = string
  default = ""
}
