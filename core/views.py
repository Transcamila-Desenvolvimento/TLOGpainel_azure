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
@acesso_permitido_apenas_para_filial('ibipora')
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

    return render(request, 'dashboard.html', {
        'data': data,
        'total_geral': total_geral,
        'total_liberado': total_liberado,
        'total_aguardando': total_aguardando,
        'tema': get_tema(),
    })

from django.db.models import Sum

@login_required
@acesso_permitido_apenas_para_filial('ibipora')
def lancamento_list(request):
    lancamentos = Lancamento.objects.select_related('destino')\
        .exclude(status='finalizado')\
        .order_by('destino__nome', '-criado_em')
    
    # Calcular totais por quantidade (soma das quantidades)
    total_liberado_quantidade = lancamentos.filter(status='liberado').aggregate(
        total=Sum('quantidade')
    )['total'] or 0
    
    total_aguardando_quantidade = lancamentos.filter(status='aguardando').aggregate(
        total=Sum('quantidade')
    )['total'] or 0
    
    total_geral_quantidade = total_liberado_quantidade + total_aguardando_quantidade
    
    destinos = Destino.objects.all().order_by('nome')

    # Preparar estatísticas por destino (usando quantidade)
    destinos_com_estatisticas = []
    for destino in destinos:
        lancamentos_destino = destino.lancamento_set.exclude(status='finalizado')
        
        # Soma das quantidades
        total_quantidade = lancamentos_destino.aggregate(
            total=Sum('quantidade')
        )['total'] or 0
        
        liberados_quantidade = lancamentos_destino.filter(status='liberado').aggregate(
            total=Sum('quantidade')
        )['total'] or 0
        
        aguardando_quantidade = lancamentos_destino.filter(status='aguardando').aggregate(
            total=Sum('quantidade')
        )['total'] or 0
        
        percentual = (liberados_quantidade / total_quantidade * 100) if total_quantidade > 0 else 0
        
        destinos_com_estatisticas.append({
            'destino': destino,
            'total_quantidade': total_quantidade,
            'liberados_quantidade': liberados_quantidade,
            'aguardando_quantidade': aguardando_quantidade,
            'percentual': round(percentual, 1)
        })

    context = {
        'lancamentos': lancamentos,
        'total_liberado': lancamentos.filter(status='liberado').count(),  # Mantém contagem de processos
        'lancamentos_aguardando': lancamentos.filter(status='aguardando'),
        'destinos': destinos,
        'destinos_com_estatisticas': destinos_com_estatisticas,
        
        # Novas variáveis para quantidade
        'total_liberado_quantidade': total_liberado_quantidade,
        'total_aguardando_quantidade': total_aguardando_quantidade,
        'total_geral_quantidade': total_geral_quantidade,
        
        'tema': get_tema(),
    }

    return render(request, 'lancamento_list.html', context)

@login_required
@acesso_permitido_apenas_para_filial('ibipora')
def processos_finalizados(request):
    lancamentos = Lancamento.objects.select_related('destino')\
        .filter(status='finalizado')\
        .order_by('destino__nome', '-criado_em')
    
    destinos = Destino.objects.all().order_by('nome')  # Ordena destinos por nome A-Z
    
    context = {
        'lancamentos': lancamentos,
        'tema': get_tema(),
    }

    return render(request, 'processos_finalizados.html', context)

@login_required
@acesso_permitido_apenas_para_filial('ibipora')
def acoes_em_lote(request):
    if request.method == 'POST':
        ids = request.POST.getlist('selecionados')
        acao = request.POST.get('acao')
        novo_status = request.POST.get('novo_status')

        if not ids:
            messages.warning(request, "Nenhum processo selecionado.")
            return redirect('processos_finalizados')

        if acao == 'excluir':
            deletados = Lancamento.objects.filter(id__in=ids, status='finalizado').delete()
            messages.success(request, f"{len(ids)} processos excluídos.")
        elif acao == 'alterar_status':
            if novo_status not in ['Aguardando', 'Liberado']:
                messages.error(request, "Selecione um status válido para reabertura.")
                return redirect('processos_finalizados')
            atualizados = Lancamento.objects.filter(id__in=ids, status='finalizado').update(
                status=novo_status.lower()
            )
            messages.success(request, f"{atualizados} processos reabertos com status '{novo_status}'.")
        else:
            messages.error(request, "Ação inválida.")

    return redirect('processos_finalizados')

@login_required
@acesso_permitido_apenas_para_filial('ibipora')
def lancamento_create(request):
    if request.method == 'POST':
        form = LancamentoForm(request.POST)
        if form.is_valid():
            lancamento = form.save(commit=False)
            lancamento.criado_por = request.user
            lancamento.save()
            return redirect('lancamento_list')
    else:
        form = LancamentoForm()

    return render(request, 'lancamento_form.html', {'form': form, 'tema': get_tema()})

@login_required
@acesso_permitido_apenas_para_filial('ibipora')
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
                    data['redirect'] = reverse('processos_finalizados')
                return JsonResponse(data)
            
            if updated_lancamento.status == 'finalizado':
                return redirect('processos_finalizados')
            return redirect('lancamento_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors}, status=400)
    
    form = LancamentoForm(instance=lancamento)
    return render(request, 'lancamento_form.html', {'form': form, 'tema': get_tema()})

@login_required
@acesso_permitido_apenas_para_filial('ibipora')
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
        
        return redirect('lancamento_list')
    
    return render(request, 'lancamento_confirm_delete.html', {
        'lancamento': lancamento,
        'tema': get_tema()
    })

@login_required
@acesso_permitido_apenas_para_filial('ibipora')
def configuracoes(request):
    configuracao, _ = ConfiguracaoDashboard.objects.get_or_create(id=1)

    if request.method == "POST":
        tema = request.POST.get("tema")
        if tema in ["claro", "escuro", "azul"]:
            configuracao.tema = tema
            configuracao.save()
        return redirect("configuracoes")

    return render(request, "configuracoes.html", {"tema": configuracao.tema})

def exportar_processos(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Processos"
    ws.append(['Processo', 'Destino', 'Quantidade', 'Data de criação', 'Status', 'Observação', 'Criado por'])

    lancamentos = Lancamento.objects.all().order_by('destino__nome', '-criado_em')
    for l in lancamentos:
        ws.append([
            l.po,
            l.destino.nome,
            l.quantidade,
            l.criado_em.strftime("%d/%m/%Y"),
            l.status,
            l.observacao,
            l.criado_por.get_full_name() or l.criado_por.username if l.criado_por else '—'
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=processos.xlsx'
    wb.save(response)
    return response


@login_required
@acesso_permitido_apenas_para_filial('ibipora')
def configuracoes_perfil(request):
    return render(request, 'configeperfil_ibi.html')