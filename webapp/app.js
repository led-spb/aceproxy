$( function(){
      //var channels = {};
      window.channels = {};

      $.expr[":"].contains = $.expr.createPseudo(function(arg) {
          return function( elem ) {
              try{
                 var expr = new RegExp(arg,  "i" );
                 return $(elem).text().search( expr ) >= 0;
              }catch(err){
                 return false;
              }
          };
      });

      $.when(
         $.getJSON( "search/?json"),  $.getJSON( "record/status/")
      ).then( function(channels, records){
         update(channels[0]);
         update_rec( records[0] );
         setInterval( function(){  $.getJSON( "record/status/", update_rec ); }, 15000);
      });

      function update_rec( data ){
         $(".channel.record").removeClass("record")

         $.each( data['show']['media'] || {}, function(channel_id, info){
             if( channels[channel_id] ){
                 var element = channels[channel_id].element;
                 element.addClass('record');
                 element.show();
                 element.find(".record-duration").text( moment().from( moment(info.started), true ) );
                 element.find(".record-size").text( filesize(info.recorded) );
             }
         });

         $(".channel .btn-record-start").show();
         $(".channel .btn-record-stop").hide();

         $(".channel.record .btn-record-start").hide();
         $(".channel.record .btn-record-stop").show();
      }

      function on_record_start(){
         channel_id = $(this).data('channel-id');
         var element = channels[channel_id]
         console.log('Start record '+channel_id);
         $.getJSON( "record/start/"+channel_id, update_rec );
      }
      function on_record_stop(){
         channel_id = $(this).data('channel-id');
         var element  = channels[channel_id].element;
         element.removeClass('record');
         console.log('Stop record '+channel_id);
         $.getJSON( "record/stop/"+channel_id, update_rec );
      }

      function create_channel(item){
          var tile = $("#templates .channel").clone();
          tile.find(".channel-name").text( item.name ).attr('href', 'channel/uuid/'+item.id );

          tile.find(".btn-record-start").data('channel-id', item.id ).click( on_record_start );
          tile.find(".btn-record-stop").data('channel-id', item.id ).click( on_record_stop);
          return tile
      }


      function update( data ){
          var cats = $("#cats");
          var categories = [];
          var holder = $(".channels");

          $.each(data, function(idx, item){
             var element = create_channel(item);
             channels[item.id] = {
                info:    item, 
                element: element 
             };
             element.appendTo( holder );
          });

          var filterByName = function( text ){
             holder.find( ".channel" ).hide();
             $( '.channel.record').show();
             if(text=="") return;
             $( '.channel:contains("'+text+'")' ).show();
          };
          var oldVal = "";
          $("#search").keyup( function(){ if(oldVal!=this.value){ filterByName(this.value); oldVal=this.value } } );
      }
   } 

);
