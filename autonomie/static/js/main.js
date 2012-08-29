/*
 * File Name : main.js
 *
 * Copyright (C) 2012 Gaston TJEBBES g.t@majerti.fr
 * Company : Majerti ( http://www.majerti.fr )
 *
 * This software is distributed under GPLV3
 * License: http://www.gnu.org/licenses/gpl-3.0.txt
 *
 */
function setPopUp(id, title){
  /*
   * Make the div with id `id` becomes a dialog with title `title`
   */
  $("#" + id).dialog(
    { autoOpen: false,
    resize:'auto',
      modal:true,
      width:"auto",
      height:"auto",
      title:title,
      open: function(event, ui){
        width =
        $('.ui-widget').css('width','60%');
        $('.ui-widget').css('height','80%');
        $('.ui-widget').css('left', '20%');
        $('.ui-widget').css('top', '10%');
        $('.ui-widget-content').css('height','auto');
      }
    });
}