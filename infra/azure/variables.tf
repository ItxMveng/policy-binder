variable "subscription_id" {
  description = "Abonnement Azure (Azure for Students)."
  type        = string
}

variable "location" {
  description = "Région Azure : France Centre (Paris)."
  type        = string
  default     = "francecentral"
}

variable "image" {
  description = "Image de l'API, publiée par GitHub Actions sur le registre GitHub."
  type        = string
  default     = "ghcr.io/itxmveng/policy-binder:latest"
}

variable "github_oidc_subject" {
  description = "Sujet OIDC présenté par GitHub Actions pour la branche main. GitHub inclut les identifiants immuables du compte et du dépôt (propriétaire@id/dépôt@id) : un dépôt renommé ou recréé ne peut pas usurper ce sujet."
  type        = string
  default     = "repo:ItxMveng@120726751/policy-binder@1414717471:ref:refs/heads/main"
}
