#!/bin/bash
# Script de prueba end-to-end del sistema

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         Sistema de Procesamiento - Test End-to-End           ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

step() {
    echo -e "${GREEN}▶${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

# 1. Verificar que Docker Compose está corriendo
step "Verificando servicios..."
if ! docker compose ps | grep -q "Up"; then
    error "Los servicios no están corriendo. Ejecuta: docker compose up -d"
    exit 1
fi
success "Servicios activos"

# 2. Verificar MySQL
step "Verificando MySQL..."
if docker compose exec -T db mysqladmin ping -h localhost -u root -proot_pass --silent; then
    success "MySQL conectado"
else
    error "MySQL no responde"
    exit 1
fi

# 3. Verificar Ollama
step "Verificando Ollama..."
if docker compose exec -T ollama ollama list > /dev/null 2>&1; then
    success "Ollama activo"
    
    # Verificar que el modelo está descargado
    if docker compose exec -T ollama ollama list | grep -q "llama3.2"; then
        success "Modelo llama3.2:3b descargado"
    else
        warning "Modelo llama3.2:3b no encontrado, descargando..."
        docker compose exec ollama ollama pull llama3.2:3b
    fi
else
    error "Ollama no responde"
    exit 1
fi

# 4. Verificar reportes en base de datos
step "Verificando reportes en base de datos..."
TOTAL_REPORTS=$(docker compose exec -T db mysql -u reports_user -preports_pass -D reports -N -B -e "SELECT COUNT(*) FROM reports;" 2>/dev/null)
PROCESSED=$(docker compose exec -T db mysql -u reports_user -preports_pass -D reports -N -B -e "SELECT COUNT(*) FROM reports WHERE procesado=1;" 2>/dev/null)
PENDING=$(docker compose exec -T db mysql -u reports_user -preports_pass -D reports -N -B -e "SELECT COUNT(*) FROM reports WHERE procesado=0;" 2>/dev/null)

echo "   Total reportes: $TOTAL_REPORTS"
echo "   Procesados: $PROCESSED"
echo "   Pendientes: $PENDING"

if [ "$TOTAL_REPORTS" -eq 0 ]; then
    warning "No hay reportes en la base de datos"
    echo ""
    echo "Para añadir un reporte de prueba:"
    echo "  1. Ejecuta el extractor: docker compose run extractor"
    echo "  2. O inserta datos manualmente en MySQL"
    exit 0
fi

# 5. Verificar índice FAISS
step "Verificando índice FAISS..."
if [ -f "shared/faiss_index/index.faiss" ]; then
    success "Índice FAISS existe"
else
    warning "Índice FAISS no creado aún (esperando primer procesamiento)"
fi

# 6. Mostrar estadísticas del processor
echo ""
step "Estadísticas del Processor:"
echo ""
docker compose exec processor python query_faiss.py stats 2>/dev/null || warning "No se pudo obtener estadísticas (¿índice vacío?)"

# 7. Prueba de búsqueda (si hay índice)
if [ -f "shared/faiss_index/index.faiss" ]; then
    echo ""
    step "Prueba de búsqueda en FAISS:"
    echo ""
    docker compose exec processor python query_faiss.py query "resultados financieros" 2>/dev/null || warning "Error en búsqueda"
fi

# 8. Verificar resúmenes generados
echo ""
step "Verificando resúmenes generados..."
HAS_SUMMARY=$(docker compose exec -T db mysql -u reports_user -preports_pass -D reports -N -B -e "SELECT COUNT(*) FROM reports WHERE resumen != '' AND resumen IS NOT NULL;" 2>/dev/null)
echo "   Reportes con resumen: $HAS_SUMMARY / $PROCESSED"

if [ "$HAS_SUMMARY" -gt 0 ]; then
    success "Hay resúmenes generados"
    echo ""
    echo "   Ejemplo de resumen:"
    docker compose exec -T db mysql -u reports_user -preports_pass -D reports -N -B -e "SELECT CONCAT('Empresa: ', empresa, '\n', 'Resumen: ', LEFT(resumen, 200), '...') FROM reports WHERE resumen != '' LIMIT 1;" 2>/dev/null
fi

# 9. Ver logs recientes del processor
echo ""
step "Últimos logs del processor:"
echo ""
docker compose logs --tail=20 processor

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                      Test Completado                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Comandos útiles:"
echo "  - Ver logs: docker compose logs -f processor"
echo "  - Búsqueda interactiva: docker compose exec processor python query_faiss.py search"
echo "  - Estadísticas: docker compose exec processor python query_faiss.py stats"
echo ""