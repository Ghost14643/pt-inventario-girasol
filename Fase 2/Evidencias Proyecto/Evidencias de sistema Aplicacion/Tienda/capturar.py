import oci
import time

# Configuración directa de credenciales
config = {
    "user": "ocid1.user.oc1..aaaaaaaasgskuko4omhr7dujre7n3n6uodaipjytyju4yntfotcioriqxu7a",
    "key_file": "C:\\Users\\isalv\\.oci\\ma.alvaradog@duocuc.cl-2026-09-27T01_22_52.885Z.pem",
    "fingerprint": "0a:77:6c:cf:ad:32:a6:8d:6b:94:86:0e:55:2d:4c:db",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaa6tsntawypljcxqtfqqfot7loliv2efd3pqjoon6szqxwkuolcaea",
    "region": "sa-santiago-1"
}

compute_client = oci.core.ComputeClient(config)
identity_client = oci.identity.IdentityClient(config)

COMPARTMENT_OCID = "ocid1.tenancy.oc1..aaaaaaaa6tsntawypljcxqtfqqfot7loliv2efd3pqjoon6szqxwkuolcaea"
SUBNET_OCID = "ocid1.subnet.oc1.sa-santiago-1.aaaaaaaazhra3n4a72hzhmq4zybbn4vs3aacf37jvzlsrelt7ftm6kpcu2ya"
SSH_PUBLIC_KEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCy14qd5aqTN5f7TdmXhQ+MZ2O/fmt9Hv+5/zvs79Imig0LCMDNSqSmMDxJKWl7WIHJxcLRX7pFLNlSYLxXvY+fI8wXB6tdB84bXEH81sf40RdXSJrJpKyqBR2rNvmXplaPP/Xve3OmHYDvvStLpl9sJsl2mGdAzLTClB0v7Bkw9tKE6k7jNhq2TT7tgsJpjMh9PFQsxlKRSyLPQpIsW2kXPvKdRQlN7CRYMGVIDbB+RmMr1sIligTHURxGxW4VBdRf4TUTUB4tPEHcbYrrqSrO/DM7n54RIw4ftN6OZswTrAsu3cqbFAFL+ubQmAZEJLAY8UX2Jvm0TSjCIc0nUNlJ isalv@Philip"

print("Consultando los parámetros de tu cuenta en Oracle Cloud...")
# Obtenemos automáticamente el Availability Domain correcto de tu tenancy
ads = identity_client.list_availability_domains(compartment_id=COMPARTMENT_OCID).data
availability_domain_name = ads[0].name

# Obtenemos la imagen de Ubuntu ARM disponible
images = compute_client.list_images(
    compartment_id=COMPARTMENT_OCID,
    shape="VM.Standard.A1.Flex",
    operating_system="Canonical Ubuntu"
).data

image_id = None
for img in images:
    if "24.04" in img.display_name and "aarch64" in img.display_name:
        image_id = img.id
        break

if not image_id and images:
    for img in images:
        if "aarch64" in img.display_name:
            image_id = img.id
            break

if not image_id:
    raise Exception("No se pudo hallar una imagen ARM compatible en la lista.")

print(f"¡Listo! AD asignado: {availability_domain_name}")
print(f"¡Imagen seleccionada! ID: {image_id}")

instance_details = oci.core.models.LaunchInstanceDetails(
    compartment_id=COMPARTMENT_OCID,
    availability_domain=availability_domain_name,
    shape="VM.Standard.A1.Flex",
    shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
        ocpus=1,
        memory_in_gbs=6
    ),
    create_vnic_details=oci.core.models.CreateVnicDetails(
        assign_public_ip=True,
        subnet_id=SUBNET_OCID
    ),
    source_details=oci.core.models.InstanceSourceViaImageDetails(
        source_type="image",
        image_id=image_id
    ),
    display_name="servidor-inventario-tesis",
    metadata={
        "ssh_authorized_keys": SSH_PUBLIC_KEY
    }
)

print("\nIniciando bucle de captura automática de capacidad en Oracle Cloud...")
print("El script intentará crear la máquina cada 60 segundos hasta conseguir espacio.\n")

while True:
    try:
        response = compute_client.launch_instance(instance_details)
        print(f"\n¡ÉXITO ROTUNDO! Servidor creado y capturado.")
        print(f"ID de la instancia: {response.data.id}")
        print("Revisa tu consola web de Oracle Cloud para ver la IP pública asignada.")
        break
    except oci.exceptions.ServiceError as e:
        if e.status == 500 or "Out of capacity" in e.message:
            print(f"Sin capacidad en este momento. Reintentando en 60 segundos... [{time.strftime('%H:%M:%S')}]", end="\r")
            time.sleep(60)
        else:
            print(f"\n[!] Ocurrió un error inesperado: {e.message}")
            break