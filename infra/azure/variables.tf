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

variable "github_repository" {
  description = "Dépôt autorisé à déployer (connexion fédérée OIDC, sans mot de passe stocké)."
  type        = string
  default     = "ItxMveng/policy-binder"
}
