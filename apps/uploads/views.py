from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView

from .models import UploadedFile
from .forms import UploadedFileForm
from apps.reconciliation.services import process_uploaded_file


class UploadedFileListView(ListView):
    model = UploadedFile
    template_name = "uploads/upload_list.html"
    context_object_name = "arquivos"
    paginate_by = 20


class UploadedFileCreateView(SuccessMessageMixin, CreateView):
    model = UploadedFile
    form_class = UploadedFileForm
    template_name = "uploads/upload_form.html"
    success_url = reverse_lazy("uploads:list")
    success_message = "Arquivo enviado com sucesso."

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível enviar o arquivo. Verifique os erros abaixo.")
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)

        result = process_uploaded_file(self.object)
        if self.object.status == UploadedFile.Status.ERRO:
            messages.error(self.request, f"Arquivo enviado, mas houve problema: {self.object.processing_notes}")
        elif result.failed:
            messages.warning(self.request, f"Arquivo importado com ressalvas: {self.object.processing_notes}")
        else:
            messages.success(self.request, f"Arquivo enviado com sucesso: {self.object.processing_notes}")

        return response


class UploadedFileDeleteView(DeleteView):
    model = UploadedFile
    template_name = "uploads/upload_confirm_delete.html"
    success_url = reverse_lazy("uploads:list")

    def form_invalid(self, form):
        messages.success(self.request, "Arquivo removido com sucesso.")
        return super().form_valid(form)
