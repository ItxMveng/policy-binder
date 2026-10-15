# API de Le Classeur sur Azure Container Apps (démo publique, crédits Azure for Students).
# Terraform crée l'infrastructure ; GitHub Actions déploie l'image et injecte les secrets
# (az containerapp secret set) : aucune valeur secrète ne passe par Terraform ni par son état.

resource "azurerm_resource_group" "main" {
  name     = "rg-policy-binder"
  location = var.location
}

# Environnement sans espace Log Analytics : pas de coût d'ingestion de journaux pour une démo.
resource "azurerm_container_app_environment" "main" {
  name                = "cae-policy-binder"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_container_app" "api" {
  name                         = "policy-binder-api"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  ingress {
    external_enabled = true
    target_port      = 8080
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    # Mise à zéro quand personne ne s'en sert ; une seule instance au plus : les limites de la
    # démo (par IP, par jour) sont tenues en mémoire.
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "api"
      image  = var.image
      cpu    = 2.0
      memory = "4Gi"

      startup_probe {
        transport               = "HTTP"
        path                    = "/health"
        port                    = 8080
        interval_seconds        = 10
        failure_count_threshold = 12
      }
    }
  }

  lifecycle {
    # Image, variables et secrets sont gérés par le workflow de déploiement.
    ignore_changes = [secret, template[0].container[0].image, template[0].container[0].env]
  }
}

# Identité de GitHub Actions : connexion fédérée (OIDC) limitée à la branche main du dépôt.
resource "azuread_application" "github" {
  display_name = "github-policy-binder-deploy"
}

resource "azuread_service_principal" "github" {
  client_id = azuread_application.github.client_id
}

resource "azuread_application_federated_identity_credential" "main_branch" {
  application_id = azuread_application.github.id
  display_name   = "github-main"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = var.github_oidc_subject
}

# Droits limités au groupe de ressources de la démo.
resource "azurerm_role_assignment" "github_deploys" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.github.object_id
}

data "azurerm_client_config" "current" {}
