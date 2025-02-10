# Procesa los argumentos y agrega comillas a los que no son flags
args=()
max_consecutive_spaces=5  # Define el máximo de espacios consecutivos permitidos

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|-u)
            args+=("$1" "$2")
            shift 2
            ;;
        -h)
            # Inicia la construcción del diccionario de headers
            header=""
            shift
            while [[ $# -gt 0 && $1 != -* ]]; do
                # Escapa las comillas dentro de cada header
                key_value=$(echo "$1" | sed 's/"/\\"/g')
                header+="$key_value, "
                shift
            done
            # Elimina la última coma y espacio, y envuelve el diccionario en {}
            header="{${header%, }}"

            # Chequea y corrige dobles llaves al inicio y al final
            if [[ $header == "{{"* ]]; then
                header="${header#\{}"
            fi
            if [[ $header == *"}}" ]]; then
                header="${header%\}}"
            fi

            args+=("-h" "\"$header\"")
            ;;
        -d)
            # Inicia la construcción del argumento para -d
            data="$2"
            shift 2
            consecutive_spaces=0

            # Continúa agregando palabras hasta que se alcance el máximo de espacios consecutivos
            while [[ $# -gt 0 && $consecutive_spaces -lt $max_consecutive_spaces ]]; do
                if [[ $1 =~ ^[[:space:]]*$ ]]; then
                    ((consecutive_spaces++))
                else
                    data+=" $1"
                    consecutive_spaces=0
                fi
                shift
            done

            # Agrega -d y su valor completo entre comillas
            args+=("-d" "\"$data\"")
            ;;
        *)
            args+=("\"$1\"")
            shift
            ;;
    esac
done

# Ejecuta el script de Python con los argumentos procesados
# echo "${args[@]}"
python code/client.py "${args[@]}"