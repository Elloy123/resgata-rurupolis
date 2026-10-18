from django.db import models


class TelefoneUtil(models.Model):
    CATEGORIA_CHOICES = [
        ('ong', 'Resgata Rurópolis'),
        ('veterinario', 'Veterinário / Clínica'),
        ('policia_ambiental', 'Polícia Ambiental'),
        ('defesa_civil', 'Defesa Civil'),
        ('prefeitura', 'Prefeitura'),
        ('outro', 'Outro'),
    ]

    nome = models.CharField(max_length=100, help_text='Ex: "Clínica Vet Amigo", "Polícia Ambiental"')
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='outro')
    telefone = models.CharField(max_length=30)
    whatsapp = models.BooleanField(default=False, help_text='Marque se este número atende por WhatsApp')
    descricao = models.CharField(max_length=255, blank=True)
    ordem = models.PositiveIntegerField(default=0, help_text='Números menores aparecem primeiro na lista')

    class Meta:
        verbose_name = 'Telefone útil'
        verbose_name_plural = 'Telefones úteis'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.telefone})'


class SobreONG(models.Model):
    titulo = models.CharField(max_length=150, default='Sobre a Resgata Rurópolis')
    texto = models.TextField(blank=True)
    email_contato = models.EmailField(blank=True)
    telefone_contato = models.CharField(max_length=30, blank=True)
    whatsapp_contato = models.CharField(max_length=30, blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    chave_pix = models.CharField(
        max_length=150, blank=True, help_text='Chave PIX exibida para doações diretas'
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sobre a ONG'
        verbose_name_plural = 'Sobre a ONG'

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
