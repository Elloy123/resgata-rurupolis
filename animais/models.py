from django.db import models
from django.utils.text import slugify


class Animal(models.Model):
    ESPECIE_CHOICES = [
        ('cachorro', 'Cachorro'),
        ('gato', 'Gato'),
        ('outro', 'Outro'),
    ]
    SEXO_CHOICES = [
        ('macho', 'Macho'),
        ('femea', 'Fêmea'),
    ]
    PORTE_CHOICES = [
        ('pequeno', 'Pequeno'),
        ('medio', 'Médio'),
        ('grande', 'Grande'),
    ]
    STATUS_CHOICES = [
        ('disponivel', 'Disponível para adoção'),
        ('em_tratamento', 'Em tratamento'),
        ('adotado', 'Adotado'),
    ]

    nome = models.CharField(max_length=100)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    especie = models.CharField(max_length=20, choices=ESPECIE_CHOICES, default='cachorro')
    raca = models.CharField(max_length=100, blank=True)
    sexo = models.CharField(max_length=10, choices=SEXO_CHOICES)
    porte = models.CharField(max_length=10, choices=PORTE_CHOICES)
    idade_aproximada = models.CharField(
        max_length=50, blank=True, help_text='Ex: "2 anos", "6 meses", "Filhote"'
    )
    descricao = models.TextField(blank=True)
    foto = models.ImageField(upload_to='animais/', blank=True, null=True)
    vacinado = models.BooleanField(default=False)
    castrado = models.BooleanField(default=False)
    disponivel_para_apadrinhamento = models.BooleanField(
        default=True,
        help_text='Se marcado, este animal aparece na página de apadrinhamento.',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponivel')
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Animal'
        verbose_name_plural = 'Animais'
        ordering = ['-data_cadastro']

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nome)
            slug = base_slug
            i = 1
            while Animal.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f'{base_slug}-{i}'
            self.slug = slug
        super().save(*args, **kwargs)


class FotoAnimal(models.Model):
    animal = models.ForeignKey(Animal, related_name='fotos_extras', on_delete=models.CASCADE)
    imagem = models.ImageField(upload_to='animais/galeria/')

    class Meta:
        verbose_name = 'Foto extra'
        verbose_name_plural = 'Fotos extras'

    def __str__(self):
        return f'Foto de {self.animal.nome}'
