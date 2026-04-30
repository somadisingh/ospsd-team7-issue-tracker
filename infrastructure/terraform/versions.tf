terraform {
  required_version = ">= 1.6.0"

  required_providers {
    render = {
      source  = "render-oss/render"
      version = ">= 1.7.0"
    }
  }
}

provider "render" {
  # Read credentials from environment variables:
  # - RENDER_API_KEY
  # - RENDER_OWNER_ID
}
