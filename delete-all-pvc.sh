for ZONE in us-central1-a us-central1-b us-central1-c us-central1-f; do
  for DISK in $(gcloud compute disks list --filter="name~'^pvc-.*' AND zone:($ZONE)" --format="value(name)"); do
    echo "Eliminando disco $DISK en zona $ZONE..."
    gcloud compute disks delete $DISK --zone=$ZONE --quiet
  done
done
