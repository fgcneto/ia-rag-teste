# Security
Nunca versionar `.env`, PATs, OAuth secrets ou chaves. O perfil Desenvolvedor é deny-by-default. O servidor MCP não confia em username fornecido pelo cliente: exige token de ator assinado e de curta duração, recarrega o usuário e reavalia ACL no banco. O collector permanece read-only.
