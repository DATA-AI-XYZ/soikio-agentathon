// Backend wiring for the live red-team (STORY-08.3.01 seam).
// The UI reads window.SOIKIO_API at run time:
//   ""            -> demo mode: renders the bundled illustrative sample (default the public site ships).
//   "<origin>"    -> live mode: POSTs the thesis to <origin>/analyze and renders the real brief.
//
// After the backend is deployed, set this to the Container App origin, e.g.
//   window.SOIKIO_API = "https://ca-soikio-prod-eus2.<region>.azurecontainerapps.io";
// Get the exact FQDN with:
//   az containerapp show -n ca-soikio-prod-eus2 -g <rg> --query properties.configuration.ingress.fqdn -o tsv
window.SOIKIO_API = "https://ca-soikio-prod-eus2.yellowbush-e6318baf.eastus2.azurecontainerapps.io";
