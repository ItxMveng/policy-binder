variable "project_id" {
  description = "Projet Google Cloud (facturation activée requise pour Cloud Run)."
  type        = string
}

variable "region" {
  description = "Région Cloud Run : Paris."
  type        = string
  default     = "europe-west9"
}

variable "image" {
  description = "Image de l'API dans Artifact Registry, par exemple europe-west9-docker.pkg.dev/<projet>/policy-binder/api:<version>."
  type        = string
}

variable "allowed_origins" {
  description = "Origines autorisées (CORS), au format JSON : [\"https://<front>.vercel.app\"]."
  type        = string
}

variable "max_instances" {
  description = "Une seule instance : les limites de la démo sont tenues en mémoire."
  type        = number
  default     = 1
}
