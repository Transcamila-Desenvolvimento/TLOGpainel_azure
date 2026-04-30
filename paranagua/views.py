# paranagua/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from .models import Destino, Lancamento, ConfiguracaoDashboard
from .forms import LancamentoForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Case, When, IntegerField
from django.urls import reverse
import openpyxl
from usuarios.decorators import acesso_permitido_apenas_para_filial 

def get_tema():
    configuracao, _ = ConfiguracaoDashboard.objects.get_or_create(id=1)
    return configuracao.tema

@login_required
@acesso_permitido_apenas_para_filial('paranagua')
def painel_tv(request):
    destinos = Destino.objects.all()
    data = []
    total_geral = 0
    total_liberado = 0
    total_aguardando = 0

    for destino in destinos:
        lancamentos = destino.lancamento_set.exclude(status='finalizado').annotate(
            prioridade=Case(
                When(status='liberado', then=0),
                default=1,
                output_field=IntegerField()
            )
        ).order_by('prioridade', '-id')

        liberado = lancamentos.filter(status='liberado').aggregate(total=Sum('quantidade'))['total'] or 0
        aguardando = lancamentos.filter(status='aguardando').aggregate(total=Sum('quantidade'))['total'] or 0
        total = liberado + aguardando

        total_liberado += liberado
        total_aguardando += aguardando
        total_geral += total

        data.append({
            'destino_nome': destino.nome,
            'lancamentos': lancamentos,
            'liberado': liberado,
            'aguardando': aguardando,
            'total': total,
        })

    return render(request, 'dashboard_paranagua.html', {
        'data': data,
        'total_geral': total_geral,
        'total_liberado': total_liberado,
        'total_aguardando': total_aguardando,
        'tema': get_tema(),
    })

@login_required
@acesso_permitido_apenas_para_filial('paranagua')
def lancamento_list(request):
    # Ordena os lançamentos por destino (nome A-Z) e depois por data de criação (mais recente primeiro)
    lancamentos = Lancamento.objects.select_related('destino')\
        .exclude(status='finalizado')\
        .order_by('destino__nome', '-criado_em')
    
    lancamentos_liberados = lancamentos.filter(status='liberado')
    lancamentos_aguardando = lancamentos.filter(status='aguardando')
    destinos = Destino.objects.all().order_by('nome')  # Ordena destinos por nome A-Z

    context = {
        'lancamentos': lancamentos,
        'total_liberado': lancamentos_liberados.count(),
        'lancamentos_aguardando': lancamentos_aguardando,
        'destinos': destinos,
        'status_choices': Lancamento.STATUS_CHOICES,
        'tema': get_tema(),
    }

    return render(request, 'lancamento_list_Paranaguá.html', context)

@login_required
@acesso_permitido_apenas_para_filial('paranagua')
def processos_finalizados(request):
    lancamentos = Lancamento.objects.select_related('destino')\
        .filter(status='finalizado')\
        .order_by('destino__nome', '-criado_em')
    
    destinos = Destino.objects.all().order_by('nome')  # Ordena destinos por nome A-Z
    
    context = {
        'lancamentos': lancamentos,
        'tema': get_tema(),
    }

    return render(request, 'processos_finalizados_paranagua.html', context)

@login_required
@acesso_permitido_apenas_para_filial('paranagua')
def acoes_em_lote(request):
    if request.method == 'POST':
        ids = request.POST.getlist('selecionados')
        acao = request.POST.get('acao')
        novo_status = request.POST.get('novo_status')

        if not ids:
            messages.warning(request, "Nenhum processo selecionado.")
            return redirect('paranagua:processos_finalizados')

        queryset = Lancamento.objects.filter(id__in=ids)

        if acao == 'excluir':
            deletados_count, _ = queryset.delete()
            messages.success(request, f"{deletados_count} processos excluídos.")
        elif acao == 'alterar_status':
            if novo_status not in ['Aguardando', 'Liberado']:
                messages.error(request, "Selecione um status válido para reabertura.")
                return redirect('paranagua:processos_finalizados')
            atualizados = queryset.update(status=novo_status.lower())
            messages.success(request, f"{atualizados} processos atualizados para '{novo_status}'.")
        else:
            messages.error(request, "Ação inválida.")

    return redirect('paranagua:processos_finalizados')


@login_required
@acesso_permitido_apenas_para_filial('paranagua')
def lancamento_create(request):
    if request.method == 'POST':
        form = LancamentoForm(request.POST)
        if form.is_valid():
            lancamento = form.save(commit=False)
            lancamento.criado_por = request.user
            lancamento.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Lançamento criado com sucesso!',
                    'redirect': reverse('paranagua:lancamento_list')
                })
                
            return redirect('paranagua:lancamento_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors}, status=400)
    else:
        form = LancamentoForm()

    return render(request, 'lancamento_form_paranagua.html', {
        'form': form, 
        'tema': get_tema(),
        'status_choices': Lancamento.STATUS_CHOICES
    })

@login_required
@acesso_permitido_apenas_para_filial('paranagua')
def lancamento_update(request, pk):
    lancamento = get_object_or_404(Lancamento, pk=pk)
    
    if request.method == 'POST':
        form = LancamentoForm(request.POST, instance=lancamento)
        if form.is_valid():
            updated_lancamento = form.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                data = {
                    'success': True,
                    'message': 'Processo atualizado com sucesso!',
                    'lancamento': {
                        'id': updated_lancamento.id,
                        'po': updated_lancamento.po,
                        'destino': {
                            'id': updated_lancamento.destino.id,
                            'nome': updated_lancamento.destino.nome
                        },
                        'quantidade': updated_lancamento.quantidade,
                        'status': updated_lancamento.status,
                        'observacao': updated_lancamento.observacao,
                        'criado_em': updated_lancamento.criado_em.strftime('%d/%m/%Y')
                    }
                }
                if updated_lancamento.status == 'finalizado':
                    data['redirect'] = reverse('paranagua:processos_finalizados')
                return JsonResponse(data)
            
            if updated_lancamento.status == 'finalizado':
                return redirect('paranagua:processos_finalizados')
            return redirect('paranagua:lancamento_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors}, status=400)
    
    form = LancamentoForm(instance=lancamento)
    return render(request, 'lancamento_form_paranagua.html', {
        'form': form, 
        'tema': get_tema(),
        'status_choices': Lancamento.STATUS_CHOICES
    })

@login_required
@acesso_permitido_apenas_para_filial('paranagua')
def lancamento_delete(request, pk):
    lancamento = get_object_or_404(Lancamento, pk=pk)
    if request.method == 'POST':
        lancamento_id = lancamento.id
        lancamento.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Processo excluído com sucesso!',
                'lancamento_id': lancamento_id
            })
        
        return redirect('paranagua:lancamento_list')
    
    return render(request, 'paranagua/lancamento_confirm_delete.html', {
        'lancamento': lancamento,
        'tema': get_tema()
    })

@login_required
@acesso_permitido_apenas_para_filial('paranagua')
def configuracoes(request):
    configuracao, _ = ConfiguracaoDashboard.objects.get_or_create(id=1)

    if request.method == "POST":
        tema = request.POST.get("tema")
        if tema in ["claro", "escuro", "azul"]:
            configuracao.tema = tema
            configuracao.save()
        return redirect("paranagua:configuracoes")

    return render(request, "configuracoes_paranaguá.html", {"tema": configuracao.tema})

@login_required
@acesso_permitido_apenas_para_filial('paranagua')
def exportar_lancamentos(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lançamentos"
    ws.append(['PO', 'Destino', 'Quantidade', 'Data de criação', 'Status', 'Observação', 'Criado por'])

    lancamentos = Lancamento.objects.all().order_by('destino__nome', '-criado_em')
    for l in lancamentos:
        ws.append([
            l.po,
            l.destino.nome,
            l.quantidade,
            l.criado_em.strftime("%d/%m/%Y"),
            l.get_status_display(),
            l.observacao,
            l.criado_por.get_full_name() or l.criado_por.username if l.criado_por else '—'
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=lancamentos_paranagua.xlsx'
    wb.save(response)
    return response