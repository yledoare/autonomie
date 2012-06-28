<%doc>
    Template for cancelled invoice readonly display
</%doc>
<%inherit file="/base.mako"></%inherit>
<%block name='content' >
<div class='container' style='overflow:hidden'>
<div>
    <span class="label label-important">></span>
    %if task.statusPersonAccount  is not UNDEFINED and task.statusPersonAccount:
        <strong>${task.get_status_str()}</strong>
        <br />
    %else:
        <strong>Aucune information d'historique ou de statut n'a pu être retrouvée</strong>
        <br />
    %endif
    %if task.has_been_validated():
        Vous ne pouvez plus modifier ce document car il a déjà été validé.
        Il porte le numéro <b>${task.officialNumber}</b>.
    %elif task.is_waiting():
        Vous ne pouvez plus modifier ce document car il est en attente de validation.
    %endif
        <br />
    %if task.invoice:
        Cet avoir est lié à la facture : <a href="${request.route_path('invoice', id=task.invoice.id)}">${task.invoice.number}</a>
    %endif
        <br />
</div>
        <div style='border:1px solid #888'>
<form id="deform" class="deform form-horizontal deform"
    accept-charset="utf-8"
    enctype="multipart/form-data"
    method="POST"
    action="${request.route_path('cancelinvoice', id=task.id, _query=dict(action='status'))}">
    % for button in submit_buttons:
        ${button.render(request)|n}
    % endfor
</form>
            ${html_datas|n}
        </div>
</div>
</%block>