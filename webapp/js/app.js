$( function(){
      var channels = {};

      $.expr[":"].contains = $.expr.createPseudo(function(arg) {
          return function( elem ) {
              var expr = new RegExp(arg,  "i" );
              return $(elem).text().search( expr ) >= 0;
          };
      });

      $.getJSON( "search/?json", update );
      $.getJSON( "rec/status/?_t=", update_rec );
      /*
      setInterval( function(){
          $.getJSON("rec/status/?_t=", update_rec );
      },  30000 );*/

      function set_favorites(list){
         Cookies.set( "fav", list.join(";") , {expires: 5*365} )
      }
      function get_favorites(){
         cookie = Cookies.get( "fav" ) || ""
         return cookie.split(";")
      }

      function update_rec( data ){
         $("#record").empty();

         $.each( data['show']['media'] || {}, function(channel_id, info){
             $("#record").
                append( '<div class="rec_item well well-sm">Rec: '+info['channel']+'<div class="btn btn-xs btn-default pull-right">Stop</div></div>')
                  .find(".btn").click( function(){
                        console.log('Stop rec', channel_id);
                        $.getJSON("record/stop/"+channel_id, update_rec );
                  });
         });
      }

      function format_channel(item){
          var tile = $('<div class="channel hidden"><div class="item_name">'+item.name+
//                     '<button class="btn btn-default btn-xs pull-right btn-rec" type="button"><span class="glyphicon recicon"></span></button>'+
                     '<button class="btn btn-default btn-xs pull-right btn-rec" type="button">Rec</button>'+
                     '<button class="btn btn-default btn-xs pull-left" type="button"><span class="glyphicon favicon"></span></button>'+
                   '</div><a href="play/'+item.id+'"><div class="item_icon" style="background-image:url('+item.logo+')"></div></a></div>');

          tile.find(".btn-rec").click( function(){
              console.log("Start recording", item.id);
              $.getJSON("record/start/"+item.id, update_rec );
          });
          return tile
      }

      function update( data ){
          var favorites = get_favorites();
          set_favorites(favorites);

          var cats = $("#cats");
          var categories = [];
          var holder = $("#channels");

          $.each(data, function(idx, item){
             var element = format_channel(item);//$('<div class="channel hidden"><a href="'+item.uri+'"><div class="item_icon" style="background-image:url('+item.logo+')"></div></a><div class="item_name"><span class="recicon glyphicon"></span>'+item.name+'<span class="favicon glyphicon"></span></div></div>');
             /*
             element.find(".recicon").parent().click( function(){
                $(this).toggleClass('active');
                var channel = channels[item.id];

                 console.log("Start recording "+channel.info.id);
             });*/
             $.each( item.tags, function(idx, value){
                  element.addClass( value );
                  if( categories.indexOf(value)==-1 ){
                     categories.push( value )
                  }
             } );
             if( favorites.indexOf(item.name) != -1 ) element.addClass( 'FAVORITES' );
             
             channels[item.id] = { info: item, holder: holder.append( element ) };
          });

          $.each(categories, function(idx, value ){
              cats.append(' <button class="btn btn-default btn-xs filter-btn" data-filter="'+value+'">'+value+'</button>' );
          })

          var filterByClass = function( filter ){
             $( "#search").val("");
             $( ".channel" ).addClass("hidden");
             $( filter.join(",") ).removeClass("hidden");
          };
          var filterByName = function( text ){
             $( ".channel" ).addClass("hidden");
             cats.find(".active").removeClass("active");

             if(text=="") return;
             $( '.channel:contains("'+text+'")' ).removeClass("hidden");
          };

          var oldVal = "";
          $("#search").keyup( function(){ if(oldVal!=this.value){ filterByName(this.value); oldVal=this.value } } );

          filterByClass( ['.FAVORITES'] );

          $(".filter-btn").on('click', function(){
               $(this).toggleClass('active').blur();
               var filter=[];
               $(".filter-btn.active").each(
                  function(){ 
                     filter.push( "."+$(this).attr('data-filter') ) 
                  }
               ).promise().done( function(){ filterByClass( filter ) } );
            }
          );

          $(".favicon").on('click', function(){
               var favorites = get_favorites()
               var channel = $(this).parent().text();
               var idx = favorites.indexOf(channel);
               if( idx!=-1 ){
                 favorites.splice(idx, 1 );
               }else{
                 favorites.push(channel);
               } 
               set_favorites(favorites);
               $(this).parents(".channel").toggleClass("FAVORITES")
          });

      } 
   } 

);

/*
function export_playlist(){
   playlist = "#EXTM3U url-tvg=\"http://www.teleguide.info/download/new3/jtv.zip\"\n"
   $.each( $(".FAVORITES"), function(i,x){
       var title = $(x).find(".item_name").text(),
           id = $(x).find(".item_id").text();

       playlist = playlist+'#EXTINF:-1 group-title="Public" tvg-name="'+title+'",'+title+"\n"
       playlist = playlist+"http://192.168.168.2:8800/channel/uuid/"+id+"\n"
   });
   console.log(playlist);
}
*/